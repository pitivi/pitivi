# Pipeline

![Pipeline functional
view](Pipeline-functional.png "Pipeline functional view")

A **Pipeline** is where all the media processing takes place in PiTiVi.

In order to hide the complexity of the underlying GStreamer pipeline, we
only have to work with 3 concepts:

-   **Producer**(s), responsible for providing data streams and the
    associated GStreamer elements
-   **Consumer**(s), responsible for consuming data streams and the
    associated GStreamer elements
-   **Action**(s), which brings in the combination of:
    -   Which Consumer(s) and Producer(s) to use, and how to link the
        associated GStreamer elements
    -   What the overall Action is, useful for the UI to provide the
        adequate interface for each action

## Pipeline

### Properties

-   Actions, the list of Actions currently being used in the pipeline
-   Producers, the list of Producers being used
-   Consumers, the list of Consumers being used

### Signals

-   `action-added`, a new Action was added to the pipeline
-   `action-removed`, an Action was removed to the pipeline

## Producer

### Properties

-   Factory, the ObjectFactory being controlled by this Producer
-   Pipeline, the Pipeline in which this Producer is being used

### Class Properties

-   CompatibleFactory, a list of ObjectFactory types this Producer can
    manage

### Signals

-   `factory-changed`

## Consumer

### Properties

-   Factory, the ObjectFactory being controlled by this Consumer
-   Pipeline, the Pipeline in which this Consumer is being used

### Class Properties

-   CompatibleFactory, a list of ObjectFactory types this Consumer can
    manage

### Signals

-   `factory-changed`

## Action

### Properties

-   Pipeline, on which it is being used, or going to be used
-   Producers, that this Action is controlling
-   Consumers, that this Action is controlling
-   State, whether it is activated or not

### Class Properties

-   CompatibleProducer, a list of Producer types this Action can handle
-   CompatibleConsumer, a list of Consumer types this Action can handle

### Signals

-   `state-changed`

# Use Cases

## Viewing a File

![Example: Viewing a
File](Pipeline-viewing-file.png "Example: Viewing a File")

This is the simplest use-case for a Pipeline, which is viewing a File.

As can be seen in the Schema, there is only one action (**ViewAction**)
which connects a SourceProducer to a LocalSinksConsumer.

## Rendering a Timeline

![Example: Rendering a
Timeline](Pipeline-rendering-timeline.png "Example: Rendering a Timeline")

In this example, we are doing 2 actions at the same time:

-   **View**ing the Timeline and,
-   **Render**ing the Timeline.

### Setting up the render

Supposing we already had our Timeline Pipeline (With the
TimelineProducer, LocalSinksConsumer and ViewAction), we just had to:

-   Create a 'RenderAction' with our existing TimelineProducer as that
    action's producer,
-   Set that Action on the Timeline
    -   **UI**: We get notified of a new Action set on the Pipeline, we
        open the adequate UI for that Action (if needed).
-   Configure the newly created 'LocalRenderConsumer' which is the
    Consumer to which our RenderAction is linked to.
    -   **UI**: The Render Timeline interface linked to our action has
        access to the configured Consumer and can open the adequate
        Configuration Widget for that Consumer.

### Actually Rendering

-   We **activate** the Action on the pipeline
    -   The pipeline gets reconfigured with all activated actions
-   We set the pipeline to PLAYING

### Finish rendering

When we are done rendering (because we got an EOS or such), we can then:

-   Remove that Action from the Pipeline (which will deactivate the
    action first, resetting the pipeline internally at the same time)
    -   **UI**: We get notified an action has been removed, we close the
        related interface/widgets.

# Relationship with GStreamer

![Relationship with
GStreamer](Pipeline-gstreamer-relationship.png "Relationship with GStreamer")
