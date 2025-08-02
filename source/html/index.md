# Blendo

Blend between two glyphs, contours or contour selections. Compatibility is required between the blend sources.

### Target

**Current Glyph** This will blend between two selected contours or two selected sections of contours in the current glyph.

**Font Selection** This will blend between two selected glyphs in the font overview. The blends will be put into new glyphs with the name defined in the “Destination Name” field.

### Mode

**Step Count** This will create the number of specified steps. The “Bias” slider allows you to influence the distribution of the blends.

**Distance** This will let you specify the distance between blend steps. The number of blends will be automatically counted by measuring the distance between the sources. *Hey, that sounds vague! What is the “distances between the sources”?* Good question. The distance is measured by looking at glyph widths, glyph bounding boxes and contour start points. If all of those are the same the distance can’t be calculated and the distance will fallback to a value of 1. This may improve over time. [Check the source code if you really want to know.](https://github.com/typesupply/blendo)

### Options

**Run Prepolator** This will let you run a Prepolator 2 match on the sources before blending. This option won’t be available if you don’t have the Prepolator 2 extension installed.

**Show Preview** This will show a preview of the blend when the target is “Current Glyph.”

#### Blend Button

Press this button to execute the blend. If the blend is not possible due to source incompatibility, you’ll get a message. When the target is “Current Glyph” the blend is undoable.


## Change Log

### 0.1

It's new. The name comes from a line of dialog in House Magazine #3 and an infamous robot. I think it was issue #3. It was in the comic. Maybe that was in #2? I’m pretty sure it was #3 because it was right before I started working there. [Please submit an issue if it was not in #3.](https://github.com/typesupply/blendo/issues) **Accuracy is very important.**