## Debugging

To debug Pitivi, you need an IDE with the ability to attach its debugger to a
remote process. Out of the box, Pitivi supports the debugger used in
[VS Code](https://code.visualstudio.com/docs/python/debugging#_local-script-debugging),
but it can be modified to work with the Professional version of
[PyCharm](https://www.jetbrains.com/help/pycharm/remote-debugging-with-product.html#remote-debug-config),
for example.

### Visual Studio Code

Assuming you have already installed the
[Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python),
install `debugpy` and open VS Code:

```
(ptv-flatpak) $ ptvenv python3 -m pip install --upgrade debugpy
[...]
(ptv-flatpak) $ code .
```

In VS Code, click the `Run and Debug` section on the left (or press
Ctrl+Shift+D). Press `Create a launch.json file`, select `Python` and then
`Remote Attach` from the list. Leave the hostname and port as default.

The `launch.json` file should open afterwards with the generated
configuration. Save the file and launch Pitivi with the `PITIVI_VSCODE_DEBUG` environment variable set to 1:

```
(ptv-flatpak) $ PITIVI_VSCODE_DEBUG=1 pitivi
[...]
Waiting for the debugger to attach...
```

Press `F5` in VS Code. If the Pitivi window shows up, your debugger is working.

### Debugging Unit Tests

You can also debug the unit tests by launching the test suite with the `PITIVI_VSCODE_DEBUG` environment variable set to 1:

```
(ptv-flatpak) $ PITIVI_VSCODE_DEBUG=1 ptvtests
[...]
Waiting for the debugger to attach...
```

Note the test suite typically limits how long a test can run and will kill any test reaching the timeout period.  Thus, when you set a breakpoint in a test, you may have to increase the timeouts to avoid it being killed while you debug:

```
(ptv-flatpak) $ PITIVI_VSCODE_DEBUG=1 ptvtests --timeout-factor 1000 [-t test_filename_or_method]
[...]
Waiting for the debugger to attach...
```
