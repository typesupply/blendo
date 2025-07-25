from vanilla.dialogs import message
from blendo import BlendoController

glyph = CurrentGlyph()
error = True
if glyph is not None:
    contours = glyph.selectedContours
    if len(contours) == 2:
        contour1, contour2 = contours
        if len(contour1.segments) == len(contour2.segments):
            BlendoController(glyph, contour1, contour2)
            error = False
if error:
    message(
        messageText="Invalid contours for blending.",
        informativeText="Please select two compatible contours."
    )