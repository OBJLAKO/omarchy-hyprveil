# Notification controls

Use the existing Omarchy popup palette (`Color.popups.text`, `Color.muted`,
`Color.urgent`, host background) and Adwaita Sans at the panel's existing type
scale. Keep left-aligned labels, native focus indicators, and the existing
spacing tokens. The palette follows the installed desktop theme rather than
introducing fixed accent colors.

A third “Notifications” tab sits beside hiding and appearance. It begins with
one protection switch, followed by the replacement mode and a compact card
preview. The existing material editor supplies the same image/shader/icon
controls as windows. Window and notification drafts stay separate. Controls
save automatically; pending edits survive a slow response, and a failed save
stays visibly unconfirmed until retry.

No new decorative frames or entry animations: the animated synthetic card is
the useful preview. Explicit copy explains that this affects captured
notifications and does not censor the entire screen. Advanced namespace and
rounding controls stay below the common controls.
