#include <Python.h>
#include <stdio.h>
#include <cairo.h>
#include <py3cairo.h>

static Pycairo_CAPI_t *Pycairo_CAPI;

/*
 * This function must be called with a range of samples, and a desired
 * width and height.
 * It will average samples if needed.
 */
static PyObject *
py_fill_surface (PyObject * self, PyObject * args)
{
  PyObject *samples;
  PyObject *sampleObj;
  int length, i;
  double sample;
  cairo_surface_t *surface;
  cairo_t *ctx;
  int width, height;
  float pixelsPerSample;
  float currentPixel;
  int samplesInAccum;
  float x = 0.;
  float lastX = 0.;
  double accum;
  double lastAccum = 0.;

  if (!PyArg_ParseTuple (args, "O!ii", &PyList_Type, &samples, &width, &height))
    return NULL;

  length = PyList_Size (samples);

  surface = cairo_image_surface_create (CAIRO_FORMAT_ARGB32, width, height);

  ctx = cairo_create (surface);

  cairo_set_source_rgb (ctx, 0.2, 0.6, 0.0);
  cairo_set_line_width (ctx, 0.5);
  cairo_move_to (ctx, 0, height);

  pixelsPerSample = width / (float) length;
  currentPixel = 0.;
  samplesInAccum = 0;
  accum = 0.;

  for (i = 0; i < length; i++) {
    /* Guaranteed to return something */
    sampleObj = PyList_GetItem (samples, i);
    sample = PyFloat_AsDouble (sampleObj);

    /* If the object was not a float or convertible to float */
    if (PyErr_Occurred ()) {
      cairo_surface_finish (surface);
      Py_DECREF (samples);
      return NULL;
    }

    currentPixel += pixelsPerSample;
    samplesInAccum += 1;
    accum += sample;
    if (currentPixel > 1.0) {
      accum /= samplesInAccum;
      cairo_line_to (ctx, x, height - accum);
      lastAccum = accum;
      accum = 0;
      currentPixel -= 1.0;
      samplesInAccum = 0;
      lastX = x;
    }
    x += pixelsPerSample;
  }

  Py_DECREF (samples);
  cairo_line_to (ctx, width, height);
  cairo_close_path (ctx);
  cairo_fill_preserve (ctx);

  return PycairoSurface_FromSurface (surface, NULL);
}

static PyMethodDef renderer_methods[] = {
  {"fill_surface", py_fill_surface, METH_VARARGS},
  {NULL, NULL}
};

static PyModuleDef module = {
  PyModuleDef_HEAD_INIT,
  "renderer",
  "Pitivi renderer module.",
  -1,
  renderer_methods, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_renderer (void)
{
  if (import_cairo () < 0) {
    g_print ("Cairo import failed.");
  }

  PyObject *m;
  m = PyModule_Create (&module);
  if (m == NULL)
    return NULL;
  return m;
}
