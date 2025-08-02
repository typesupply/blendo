import math
from fontTools.pens.pointPen import GuessSmoothPointPen
from fontMath import MathGlyph
from fontParts.base.base import interpolate
from fontParts.base.bPoint import (
    absoluteBCPIn,
    absoluteBCPOut
)
from fontParts.world import (
    RFont,
    RGlyph
)
from vanilla.dialogs import message
import ezui
from merz import MerzPen
from mojo.roboFont import (
    CurrentFont,
    CurrentGlyph
)
from mojo.UI import (
    CurrentGlyphWindow,
    AllGlyphWindows
)
from mojo.subscriber import (
    Subscriber,
    registerCurrentGlyphSubscriber
)

debug = __name__ == "__main__"

try:
    import prepolator
    havePrepolator = True
except ImportError:
    havePrepolator = False
if not debug:
    havePrepolator = False

extensionStub = "com.typesupply.Blendo."
glyphEditorPreviewContainerIdentifier = extensionStub + "PreviewContainer"
glyphEditorPreviewPathLayerName = extensionStub + "PathLayer"

fallbackOutputGlyphName = "blend"




class BlendoController(Subscriber, ezui.WindowController):

    debug = debug

    def build(self):
        content = """
        = TwoColumnForm

        : Target:
        (X) Current Glyph @targetModeRadioButtons
        ( ) Font Selectiom

        : Destination Name:
        [_ _] @outputGlyphName

        : Mode:
        (X) Step Count @blendModeRadioButtons
        ( ) Distance

        :
        [_ 10 _](±) @valueField

        : Bias:
        --X-- [_ 0.5 _] @biasSlider

        :
        [X] Run Prepolator @runPrepolatorCheckbox
        :
        [X] Show Preview @showPreviewCheckbox

        =---=

        (Blend) @blendButton
        """
        titleColumnWidth = 120
        itemColumnWidth = 150
        descriptionData = dict(
            content=dict(
                titleColumnWidth=titleColumnWidth,
                itemColumnWidth=itemColumnWidth
            ),
            outputGlyphName=dict(
                placeholder=fallbackOutputGlyphName
            ),
            valueField=dict(
                valueType="integer",
                minValue=1,
                maxValue=999,
                value=5,
                textFieldWidth=35,
            ),
            biasSlider=dict(
                minValue=0,
                maxValue=1,
                value=0.5,
                tickMarks=3
            ),
            runPrepolatorCheckbox=dict(
                value=havePrepolator
            )
        )
        self.w = ezui.EZPanel(
            content=content,
            descriptionData=descriptionData,
            controller=self,
            title="Blendo",
            activeItem="valueField"
        )
        self.w.getItem("runPrepolatorCheckbox").enable(havePrepolator)

    def started(self):
        for glyphEditor in AllGlyphWindows():
            self.makeGlyphEditorPreviewLayers(glyphEditor)
        self.targetModeRadioButtonsCallback(None)
        self.w.open()
        self.w.makeKey()

    def windowWillClose(self, sender):
        for glyphEditor in AllGlyphWindows():
            self.destroyGlyphEditorPreviewLayers(glyphEditor)

    # ----------
    # Properties
    # ----------

    @property
    def targetMode(self):
        modes = {
            0 : "currentGlyph",
            1 : "fontSelection",
        }
        mode = self.w.getItemValue("targetModeRadioButtons")
        return modes[mode]

    @property
    def blendMode(self):
        modes = {
            0 : "steps",
            1 : "distance",
        }
        mode = self.w.getItemValue("blendModeRadioButtons")
        return modes[mode]

    @property
    def font(self):
        return CurrentFont()

    @property
    def glyph(self):
        return CurrentGlyph()

    @property
    def glyphEditor(self):
        return CurrentGlyphWindow()

    @property
    def showPreview(self):
        return self.w.getItemValue("showPreviewCheckbox")

    # -------------
    # Notifications
    # -------------

    def glyphEditorDidOpen(self, info):
        editor = info["glyphEditor"]
        self.makeGlyphEditorPreviewLayers(editor)

    def glyphEditorDidSelectAll(self, info):
        self.updateGlyphEditorPreview()

    def glyphEditorDidDeselectAll(self, info):
        self.updateGlyphEditorPreview()

    def currentGlyphDidSetGlyph(self, info):
        self.updateGlyphEditorPreview()

    def currentGlyphDidChangeOutline(self, info):
        self.updateGlyphEditorPreview()

    def currentGlyphDidEndChangeSelection(self, info):
        self.updateGlyphEditorPreview()

    # ---------
    # Callbacks
    # ---------

    def targetModeRadioButtonsCallback(self, sender):
        onOff = self.targetMode == "fontSelection"
        form = self.w.getItem("content")
        # XXX new ezui feature
        if hasattr(form, "showGroup"):
            form.showGroup("outputGlyphName", onOff)
            self.w.resizeToFitContent()
        self.updateGlyphEditorPreview()

    def blendModeRadioButtonsCallback(self, sender):
        onOff = self.blendMode == "steps"
        form = self.w.getItem("content")
        # XXX new ezui feature
        if hasattr(form, "showGroup"):
            form.showGroup("biasSlider", onOff)
            self.w.resizeToFitContent()
        self.updateGlyphEditorPreview()

    def valueFieldCallback(self, sender):
        self.updateGlyphEditorPreview()

    def biasSliderCallback(self, sender):
        self.updateGlyphEditorPreview()

    def showPreviewCheckboxCallback(self, sender):
        self.updateGlyphEditorPreview()

    def blendButtonCallback(self, sender):
        glyphs = self.buildGlyphs()
        targetMode = self.targetMode
        if targetMode == "currentGlyph":
            if not glyphs:
                self.showMessage(
                    messageText="Current glyph selection is not interpolatable.",
                    informativeText="Select two contours or point sequences that are compatible."
                )
                return
            glyph = self.glyph
            with glyph.undo("Blend"):
                pen = glyph.getPen()
                for otherGlyph in glyphs:
                    otherGlyph.draw(pen)
        elif targetMode == "fontSelection":
            font = self.font
            if not glyphs:
                self.showMessage(
                    messageText="The current font selection is not interpolatable.",
                    informativeText="Select two glyphs that are compatible."
                )
                return
            baseName = self.w.getItemValue("outputGlyphName")
            if not baseName:
                baseName = fallbackOutputGlyphName
            for i, glyph in enumerate(glyphs):
                glyph.name = f"{baseName}.{i + 1}"
                font.insertGlyph(glyph.asFontParts())

    # -------
    # Preview
    # -------

    def makeGlyphEditorPreviewLayers(self, glyphEditor):
        container = glyphEditor.extensionContainer(
            identifier=glyphEditorPreviewContainerIdentifier,
            location="background",
            clear=True
        )
        container.appendPathSublayer(
            name=glyphEditorPreviewPathLayerName,
            fillColor=None,
            strokeColor=(0.5, 0.5, 0.5, 0.5),
            strokeWidth=1
        )

    def destroyGlyphEditorPreviewLayers(self, glyphEditor):
        container = glyphEditor.extensionContainer(
            identifier=glyphEditorPreviewContainerIdentifier,
            location="background",
            clear=True
        )

    def getGlyphEditorPreviewContainer(self, glyphEditor):
        container = glyphEditor.extensionContainer(
            identifier=glyphEditorPreviewContainerIdentifier,
            location="background",
            clear=False
        )
        return container

    def updateGlyphEditorPreview(self):
        glyphEditor = self.glyphEditor
        if glyphEditor is None:
            return
        container = self.getGlyphEditorPreviewContainer(glyphEditor)
        glyphs = None
        if self.showPreview:
            if self.targetMode == "currentGlyph":
                glyphs = self.buildGlyphs()
            if glyphs:
                pathLayer = container.getSublayer(glyphEditorPreviewPathLayerName)
                pen = MerzPen()
                for glyph in glyphs:
                    glyph.draw(pen)
                pathLayer.setPath(pen.path)
        container.setVisible(bool(glyphs))

    # -------
    # Builder
    # -------

    def buildGlyphs(self):
        targetMode = self.targetMode
        if targetMode == "currentGlyph":
            glyph = self.glyph
            if glyph is None:
                return None
            glyph1, glyph2 = getGlyphSelectionAsGlyphs(glyph)
            if None in (glyph1, glyph2):
                return None
            compatible = getGlyphCompatibility(glyph1, glyph2)
            if not compatible:
                return None
        elif targetMode == "fontSelection":
            font = self.font
            selectedGlyphs = font.selectedGlyphs
            if len(selectedGlyphs) != 2:
                return None
            glyph1, glyph2 = selectedGlyphs
            compatible = getGlyphCompatibility(glyph1, glyph2)
            if not compatible:
                return None
        haveSinglePoint = True in [len(contour.segments) for contour in glyph1]
        haveOpenContour = True in [contour.open for contour in glyph1]
        font = RFont(showInterface=False)
        font.info.unitsPerEm = self.font.info.unitsPerEm
        font.insertGlyph(glyph1, name="source1")
        font.insertGlyph(glyph2, name="source2")
        glyph1 = font["source1"]
        glyph2 = font["source2"]
        if not any((haveSinglePoint, haveOpenContour)):
            if all((havePrepolator, self.w.getItemValue("runPrepolatorCheckbox"))):
                group = prepolator.MakeCompatibilityGroup(
                    model=glyph1.asDefcon(),
                    glyphs=(glyph2.asDefcon(),)
                )
                group.strictOffCurves = False
                group.matchModel()
                del group
        mathGlyph1 = MathGlyph(glyph1)
        mathGlyph2 = MathGlyph(glyph2)
        blendMode = self.w.getItemValue("blendModeRadioButtons")
        count = self.w.getItemValue("valueField")
        if blendMode == 1:
            distance = calcDistanceBetweenGlyphs(glyph1, glyph2)
            if not distance:
                return None
            bias = 0.5
            count = math.ceil(distance / count)
        else:
            bias = self.w.getItemValue("biasSlider")
            count += 1
        glyphs = []
        for v in range(1, count):
            v /= count
            glyph = biasedInterpolate(
                mathGlyph1,
                mathGlyph2,
                v,
                bias
            )
            final = RGlyph()
            final.name = "blendGlyph"
            glyph = glyph.extractGlyph(final.asDefcon())
            glyphs.append(glyph)
        return glyphs


# -------
# Support
# -------

def biasedInterpolate(a, b, v, bias=0.5):
    gamma = 2 ** (2 * (bias - 0.5))
    vBiased = v ** gamma
    return a + (b - a) * vBiased

def calcDistanceBetweenGlyphs(glyph1, glyph2):
    # try widths
    if glyph1.width != glyph2.width:
        return abs(glyph1.width - glyph2.width)
    # try bounds
    bounds1 = glyph1.bounds
    bounds2 = glyph2.bounds
    if None in (bounds1, bounds2):
        return None
    xMin1, yMin1, xMax1, yMax1 = bounds1
    xMin2, yMin2, xMax2, yMax2 = bounds2
    distance = calcDistance((xMin1, yMin1), (xMin2, yMin2))
    distance = abs(distance)
    if distance != 0:
        return distance
    # try start points
    for contourIndex, contour1 in enumerate(glyph1.contours):
        contour2 = glyph2.contours[contourIndex]
        pt1 = (contour1.segments[0].onCurve)
        pt1 = (pt1.x, pt1.y)
        pt2 = (contour2.segments[0].onCurve)
        pt2 = (pt2.x, pt2.y)
        if pt1 != pt2:
            distance = calcDistance(pt1, pt2)
            distance = abs(distance)
            if distance != 0:
                return distance
    # fallback
    return 1

def calcDistance(pt1, pt2):
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

def getGlyphSelectionAsGlyphs(glyph):
    fallback = (None, None)
    selectedContours = glyph.selectedContours
    if not selectedContours:
        return fallback
    if len(selectedContours) > 2:
        return fallback
    if len(selectedContours) == 2:
        contour1, contour2 = selectedContours
        glyph1 = makeGlyphFromContour(contour1)
        glyph2 = makeGlyphFromContour(contour2)
    else:
        selectedBPoints = getContourSelectedBPointRanges(selectedContours[0], rangeCount=2)
        if selectedBPoints is None:
            return fallback
        selectedBPoints1, selectedBPoints2 = selectedBPoints
        glyph1 = makeGlyphFromBPoints(selectedBPoints1)
        glyph2 = makeGlyphFromBPoints(selectedBPoints2)
    return glyph1, glyph2

def makeGlyphFromContour(contour):
    if len(contour.selectedSegments) == len(contour.segments):
        glyph = RGlyph()
        contour.draw(glyph.getPen())
        return glyph
    else:
        selectedBPoints = getContourSelectedBPointRanges(contour)
        if selectedBPoints is None:
            return None
        glyph = makeGlyphFromBPoints(selectedBPoints[0])
        return glyph
    return None

def makeGlyphFromBPoints(bPoints):
    points = []
    for bPoint in bPoints:
        bcpIn = bPoint.bcpIn
        anchor = bPoint.anchor
        bcpOut = bPoint.bcpOut
        bcpIn = absoluteBCPIn(anchor, bcpIn)
        bcpOut = absoluteBCPOut(anchor, bcpOut)
        points.append((bcpIn, None))
        points.append((anchor, "curve"))
        points.append((bcpOut, None))
    points.pop(0)
    points.pop(-1)
    anchor = points.pop(0)[0]
    points.insert(0, (anchor, "move"))
    glyph = RGlyph()
    smoothPen = GuessSmoothPointPen(glyph.getPointPen())
    smoothPen.beginPath()
    for point, pointType in points:
        smoothPen.addPoint(point, pointType)
    smoothPen.endPath()
    return glyph

def getContourSelectedBPointRanges(contour, rangeCount=1):
    indexes = [bPoint.index for bPoint in contour.selectedBPoints]
    ranges = getContiguousIndexes(indexes, len(contour.bPoints))
    if len(ranges) != rangeCount:
        return None
    bPoints = contour.bPoints
    bPointRanges = []
    for range in ranges:
        bPointRanges.append([])
        for i in range:
            bPoint = bPoints[i]
            bPointRanges[-1].append(bPoint)
    return bPointRanges

def getContiguousIndexes(indexes, length):
    if not indexes:
        return []
    indexes = sorted(indexes)
    ranges = []
    last = length - 1
    previous = None
    for i in indexes:
        # no previous index,
        # start a new range.
        if previous is None:
            ranges.append([i])
            previous = i
            continue
        d = i - previous
        # only one step, continue the range.
        if d == 1:
            ranges[-1].append(i)
            previous = i
            continue
        # greater than one difference,
        # start a new range.
        if d != 1:
            ranges.append([i])
            previous = i
            continue
        # if the last index arrives here
        # start a new range so that it can
        # be looped to the beginning.
        if i == last:
            ranges.append([i])
            previous = i
            continue
        ranges[-1].append(i)
        previous = i
    # if the last range ends with the last index
    # and the first range begins with the first index
    # insert the last range into the first range
    if all((len(ranges) > 1, ranges[-1][-1] == last, ranges[0][0] == 0)):
        for i in reversed(ranges.pop(-1)):
            ranges[0].insert(0, i)
    return ranges

def getGlyphCompatibility(glyph1, glyph2):
    if len(glyph1.contours) != len(glyph2.contours):
        return False
    if len(glyph1.components) != len(glyph2.components):
        return False
    for i in range(len(glyph1.contours)):
        contour1 = glyph1.contours[i]
        contour2 = glyph2.contours[i]
        if len(contour1.segments) != len(contour2.segments):
            return False
        if len(set((contour1.open, contour2.open))) != 1:
            return False
    return True


# -----------------
# External Function
# -----------------

def OpenBlendo():
    registerCurrentGlyphSubscriber(BlendoController)

if __name__ == "__main__":
    OpenBlendo()
