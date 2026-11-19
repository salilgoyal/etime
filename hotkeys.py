"""Global hotkey registration using NSEvent global monitor."""

from typing import Callable, Dict, Optional
from AppKit import NSEvent, NSKeyDownMask
from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

# Modifier flag masks (from NSEvent)
NSControlKeyMask = 1 << 18
NSAlternateKeyMask = 1 << 19
NSCommandKeyMask = 1 << 20
NSShiftKeyMask = 1 << 17

# Required modifiers: Control + Option + Command
HOTKEY_MODIFIERS = NSControlKeyMask | NSAlternateKeyMask | NSCommandKeyMask


class HotkeyManager:
    """Manages global hotkey registration and handling via NSEvent."""

    def __init__(self):
        """Initialize hotkey manager."""
        self.callbacks: Dict[tuple[int, bool], Callable] = {}
        # Bare (unmodified) keys, live only while command_mode_active() is true.
        # They can only ever fire through the local monitor: the global monitor
        # can observe keys typed into other apps but not swallow them, so a bare
        # key there would also reach the app you're typing in.
        self.command_keys: Dict[tuple[int, bool], Callable] = {}
        self.command_mode_active: Optional[Callable[[], bool]] = None
        self._monitor = None
        # Local monitor fires for etime's OWN windows (the global monitor never
        # does), so hotkeys still work when an etime window is frontmost.
        self._local_monitor = None

    def register(self, keycode: int, callback: Callable, shift: bool = False) -> None:
        """
        Register a hotkey callback.

        Args:
            keycode: Virtual key code (e.g., KEY_N).
            callback: Function to call when hotkey is pressed.
            shift: If True, requires Shift as additional modifier.
        """
        self.callbacks[(keycode, shift)] = callback

    def register_command_key(self, keycode: int, callback: Callable, shift: bool = False) -> None:
        """Register a bare key that acts only while etime is in command mode."""
        self.command_keys[(keycode, shift)] = callback

    def start(self) -> bool:
        """
        Start listening for hotkeys.

        Returns:
            True if successful, False if accessibility permissions not granted.
        """
        # With the prompt option, macOS also adds the app to the Accessibility
        # list (as "etime" when launched from etime.app) and offers to open it.
        if not AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}):
            print("Error: Accessibility permissions not granted.")
            print("Please enable etime in System Settings → Privacy & Security → Accessibility")
            return False

        self._monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self._handle_event
        )
        # Also listen for events targeting etime's own windows.
        self._local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self._handle_local_event
        )

        if not self._monitor:
            print("Error: Failed to create NSEvent global monitor")
            return False

        print("Hotkey manager started successfully (NSEvent monitor)")
        return True

    def _dispatch(self, event) -> bool:
        """Check an event against registered hotkeys; invoke callback if matched.

        Returns True if a hotkey callback was fired (so the local monitor can
        swallow the event), False otherwise.
        """
        try:
            flags = event.modifierFlags()
            keycode = event.keyCode()

            # Check if our modifiers are pressed (mask to only the ones we care about)
            relevant_flags = flags & (NSControlKeyMask | NSAlternateKeyMask | NSCommandKeyMask)
            if relevant_flags != HOTKEY_MODIFIERS:
                return False

            shift_pressed = bool(flags & NSShiftKeyMask)
            key = (keycode, shift_pressed)
            if key in self.callbacks:
                try:
                    self.callbacks[key]()
                except Exception as e:
                    print(f"Error in hotkey callback for keycode {keycode}: {e}")
                return True
            return False
        except Exception as e:
            print(f"Error in event handler: {e}")
            return False

    def _handle_event(self, event) -> None:
        """Handle a global key-down event (from other applications)."""
        self._dispatch(event)

    def _handle_local_event(self, event):
        """Handle a key-down event targeting an etime window.

        Local-monitor handlers MUST return the event to let it propagate, or
        None to consume it. We consume matched hotkeys so they don't also type
        into our own dialogs.
        """
        if self._dispatch(event):
            return None
        if self._dispatch_command_key(event):
            return None
        return event

    def _dispatch_command_key(self, event) -> bool:
        """Handle a bare key in command mode. Returns True to swallow the event.

        Every unmodified key is swallowed in command mode, bound or not: the
        overlay has nothing to type into, so an unbound key would only beep.
        Keys with ⌘/⌃/⌥ pass through so ⌘Tab, ⌘Q and friends keep working.
        """
        try:
            if self.command_mode_active is None or not self.command_mode_active():
                return False
            flags = event.modifierFlags()
            if flags & (NSControlKeyMask | NSAlternateKeyMask | NSCommandKeyMask):
                return False
            callback = self.command_keys.get((event.keyCode(), bool(flags & NSShiftKeyMask)))
            if callback:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in command key callback for keycode {event.keyCode()}: {e}")
            return True
        except Exception as e:
            print(f"Error in command key handler: {e}")
            return False

    def check_and_repair(self) -> None:
        """Health check — recreate monitor if it was lost."""
        if self._monitor is None:
            print("WARNING: NSEvent monitor is None — recreating")
            self.force_recreate()

    def force_recreate(self) -> bool:
        """Tear down and recreate the event monitor."""
        print("Force-recreating NSEvent monitor...")
        self.stop()
        self._monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self._handle_event
        )
        self._local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, self._handle_local_event
        )
        if self._monitor:
            print("NSEvent monitor recreated successfully")
            return True
        else:
            print("ERROR: NSEvent monitor recreation failed")
            return False

    def stop(self):
        """Stop listening for hotkeys."""
        if self._monitor:
            NSEvent.removeMonitor_(self._monitor)
            self._monitor = None
        if self._local_monitor:
            NSEvent.removeMonitor_(self._local_monitor)
            self._local_monitor = None
