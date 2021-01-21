---
short-description: How to enable and use the GTK Inspector
...

# Hacking the UI

The [GTK
Inspector](https://developer.gnome.org/gtk4/stable/interactive-debugging.html)
allows changing the widgets properties on the fly.

The GTK Inspector can be activated by pressing `Ctrl-Shift-i` only if
enabled in settings with:

```
(ptv-flatpak) $ ptvenv gsettings set org.gtk.Settings.Debug enable-inspector-keybinding true
```
