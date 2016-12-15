from PyQt4 import Qt
import PyQt4.Qwt5 as Qwt
from PyQt4.Qt import QSize

class Vplot(Qwt.QwtPlot):
    def __init__(self,*args):
        Qwt.QwtPlot.__init__(self, *args)
        self.alignScales()
        self.x = []
        self.y = []
        self.plotLayout().setMargin(0)
        self.plotLayout().setCanvasMargin(0)
        self.plotLayout().setAlignCanvasToScales(True)
        self.curve = Qwt.QwtPlotCurve()
        self.curve.attach(self)
        self.startTimer(1000)

    def alignScales(self):
        self.canvas().setFrameStyle(Qt.QFrame.Box | Qt.QFrame.Plain)
        self.canvas().setLineWidth(1)
        for i in range(Qwt.QwtPlot.axisCnt):
            scaleWidget = self.axisWidget(i)
            if scaleWidget:
                scaleWidget.setMargin(0)
            scaleDraw = self.axisScaleDraw(i)
            if scaleDraw:
                scaleDraw.enableComponent(
                    Qwt.QwtAbstractScaleDraw.Backbone, False)

    def addPoint(self,x,y):
        # only keep 1000 points
        if (len(self.x)>1000):
            self.x.pop(0)
            self.y.pop(0)

        self.x.append(x)
        self.y.append(y)

    def timerEvent(self, e):
        self.curve.setData(self.x, self.y)
        self.replot()
    
    def sizeHint(self, *args, **kwargs):
        return  QSize(150,150)
    
    def minimumSizeHint(self, *args, **kwargs):
        return QSize(30,30)
