from random import uniform
from math import sin

class ALG:
    def __init__(self,alg_type):
        self.type=alg_type
        self.xValueRange=[x/100.0 for x in range(0,314,1)]
        self.preValue=0.0
        self.index=0
        self.yValueMax=10
        self.yValueStart=0
        self.yValue=0
        self.step=1
        self.pos = 0
        self.dir=1

    def getNext(self):
        self.calc()
        return (self.xValue,self.yValue)

    def calc(self):
        if self.index >= len(self.xValueRange):
            self.index = 0
        if (self.type == "Sin"):
            self.yValue=sin(self.xValueRange[self.index-1])
            self.preValue=self.yValue
        elif (self.type == "Random"):
            self.yValue=uniform(0,9)
            self.preValue=self.yValue
        elif (self.type == "Step"):
            if (self.yValue>=3):
                self.dir = -1
            if (self.yValue<=0):
                self.dir = 1
            if (self.index % 30 == 0):
                self.yValue+=self.dir
        elif (self.type == "Triangle"):
            if (self.yValue>=self.yValueMax):
                self.step = abs(self.step)*-1
            if (self.yValue<=self.yValueStart):
                self.step = abs(self.step)
            self.yValue+=self.step
        else:
            self.yValue=0
            self.preValue=0

        self.xValue = self.pos
        self.index+=1
        self.pos+=1
