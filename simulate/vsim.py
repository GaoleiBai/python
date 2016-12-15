# _*_ coding: utf-8
from __future__ import division
import threading
from threading import Lock
from PyQt4 import QtCore
from PyQt4 import QtGui, uic
import datetime

from PyQt4.QtGui import QFileDialog,QPixmap
import gpxpy
import json,base64,urllib,sys,os
from suds.client import Client
from  assemble import can_1_assemble,can_2_assemble,ad_assemble,gps_assemble
from vplot import Vplot
from alg import ALG
from utils import printStr2Hex
import socket
from kafka import SimpleProducer, KafkaClient
import time
import logging



class Counter():
    def __init__(self):
        self.can = 0
        self.ad = 0
        self.gps = 0
        self.can_error = 0
        self.ad_error = 0
        self.gps_error = 0
        self.can_lock = Lock()
        self.ad_lock = Lock()
        self.gps_lock = Lock()
        self.can_error_lock = Lock()
        self.ad_error_lock = Lock()
        self.gps_error_lock = Lock()

    def increase_can(self):
        self.can_lock.acquire()
        self.can+=1
        self.can_lock.release()
        
    def increase_ad(self):   
        self.ad_lock.acquire()
        self.ad+=1
        self.ad_lock.release()

    def increase_gps(self):   
        self.gps_lock.acquire()
        self.gps+=1
        self.gps_lock.release()
        
    def increase_can_error(self):
        self.can_error_lock.acquire()
        self.can_error+=1
        self.can_error_lock.release()
        
    def increase_ad_error(self):   
        self.ad_error_lock.acquire()
        self.ad_error+=1
        self.ad_error_lock.release()

    def increase_gps_error(self):   
        self.gps_error_lock.acquire()
        self.gps_error+=1
        self.gps_error_lock.release()


def correct_gps(longtitude,latitude):    
    
    #Use baidu api to correct coordinate
    url='http://api.map.baidu.com/ag/coord/convert?from=0&to=4&x=%f&y=%f' %(longtitude,latitude)
    correct_data = urllib.urlopen(url).read()
    json_data = json.loads(correct_data)
    print json_data
    x1=base64.b64decode(json_data["x"])
    y1=base64.b64decode(json_data["y"])
    return x1,y1


class SimWindow(QtGui.QMainWindow):
    def __init__(self):
        super(SimWindow, self).__init__()
        uic.loadUi('ui/simwindow.ui', self)
        self.__center()
        self.show()
        self.__initPlot()
        self.__setDefaultValue()
        self.__setEventConnector()
        
    def __center(self):
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def __initPlot(self):

        self.can_1_sig_1_canvas = Vplot()
        self.can_1_sig_2_canvas = Vplot()
        self.can_1_sig_3_canvas = Vplot()
        self.can_2_sig_1_canvas = Vplot()
        self.can_2_sig_2_canvas = Vplot()
        self.can_2_sig_3_canvas = Vplot()
        self.ad_1_canvas = Vplot()
        self.ad_2_canvas = Vplot()

        self.can_1_sig_1_plot.addWidget(self.can_1_sig_1_canvas)
        self.can_1_sig_2_plot.addWidget(self.can_1_sig_2_canvas)
        self.can_1_sig_3_plot.addWidget(self.can_1_sig_3_canvas)
        self.can_2_sig_1_plot.addWidget(self.can_2_sig_1_canvas)
        self.can_2_sig_2_plot.addWidget(self.can_2_sig_2_canvas)
        self.can_2_sig_3_plot.addWidget(self.can_2_sig_3_canvas)
        self.ad_1_plot.addWidget(self.ad_1_canvas)
        self.ad_2_plot.addWidget(self.ad_2_canvas)

        #newThread = calcThread(1,"mythread", self.can_1_sig_1_canvas,1000)
        #newThread.start()

    def __setDefaultValue(self):
       
        logo1 = QPixmap("icons/car.png")
        logo1=logo1.scaled(64, 64, QtCore.Qt.KeepAspectRatio)
        self.logo_1_u.setPixmap(logo1)
        self.logo_1_u.show()
        logo2 = QPixmap("icons/signal.png")
        logo2=logo2.scaled(32, 32, QtCore.Qt.KeepAspectRatio)
        self.logo_2_u.setPixmap(logo2)
        self.logo_2_u.show()
        
        # default VIN , from the seqence 1
        self.vin_u.setText("1")
        # default prefix of VIN ,length is 13 characters
        self.vin_prefix_u.setText("PLV0000000000")
        # enable VIN prefix by default
        self.use_vin_prefix_u.setChecked(True)
        # set thread number to 1 by default
        self.thread_number_u.setText("1")
        # set CAN message interval time to 100ms
        self.can_1_interval_u.setText("10")
        self.can_2_interval_u.setText("10")
        #set A/D interval time to 100ms
        self.ad_1_interval_u.setText("10")
        self.ad_2_interval_u.setText("10")
        #set Alg options
        self.alg_options =  ["Sin", "Step","Triangle", "Random"]
        self.can_1_sig_1_alg_u.addItems(self.alg_options)
        self.can_1_sig_2_alg_u.addItems(self.alg_options)
        self.can_1_sig_3_alg_u.addItems(["Triangle"])
        self.can_2_sig_1_alg_u.addItems(["Step"])
        self.can_2_sig_2_alg_u.addItems(["Step"])
        self.can_2_sig_3_alg_u.addItems(["Step"])
        self.ad_1_alg_u.addItems(self.alg_options)
        self.ad_2_alg_u.addItems(self.alg_options)
        
        
        #Set CAN message 1   ABS_ESC_1 (0x92) DLC=8 CycleTime=20ms
        self.can_1_enable_u.setChecked(True)
        self.can_1_enable_u.setText("ABS_ESC_1 (0x92/146D)")
        # Unit=rpm StartBits=12 length=16  ByteOrder=Intel Offset=0 Factor=0.0625 Min=0 Max=4095.81 valueType=unsigned
        self.can_1_sig_1_name_u.setText("WheelSpeed_FL")
        # Unit=rpm StartBits=28 length=16  ByteOrder=Intel Offset=0 Factor=0.0625 Min=0 Max=4095.81 valueType=unsigned
        self.can_1_sig_2_name_u.setText("WheelSpeed_FR")
        # Unit=bar StartBits=48 length=8  ByteOrder=Intel Offset=0 Factor=1 Min=0 Max=254 ValueType=unsigned
        self.can_1_sig_3_name_u.setText("BrakePressure")
        
        #Set CAN message 2   ABS_ESC_1 (0x92) DLC=2 CycleTime=100ms
        self.can_2_enable_u.setChecked(True)
        self.can_2_enable_u.setText("BCM_2 (0x104/260D)")
        # Unit=bits StartBits=10 length=2  ByteOrder=Intel Offset=0 Factor=1 Min=0 Max=3 valueType=unsigned
        self.can_2_sig_1_name_u.setText("TurnIndictors")
        # Unit=bits StartBits=8 length=2  ByteOrder=Intel Offset=0 Factor=1 Min=0 Max=3 valueType=unsigned
        self.can_2_sig_2_name_u.setText("LowBeam")
        # Unit=bits StartBits=12 length=2  ByteOrder=Intel Offset=0 Factor=1 Min=0 Max=3 valueType=unsigned
        self.can_2_sig_3_name_u.setText("TransportMode")
        
        #self.soap_enable_button_u.setChecked(True)
        self.soap_server_address_u.setText("http://192.168.5.16:8080/PacketDispatcher/Packet?wsdl")
        self.soap_server_address_u.setEnabled(False)
        self.soap_server_address_u.setCursorPosition(0)
        
        self.kafka_enable_button_u.setChecked(True)
        self.kafka_server_address_u.setText("localhost:9092")
        #self.kafka_server_address_u.setEnabled(False)
        self.kafka_server_address_u.setCursorPosition(0)
        
        self.start_button_u.setEnabled(True)
        self.stop_button_u.setEnabled(False)
        self.pause_button_u.setEnabled(False)

        self.start_button_log_u.setEnabled(True)
        self.stop_button_log_u.setEnabled(False)
        self.pause_button_log_u.setEnabled(False)

        self.start_button_u.setIcon(QtGui.QIcon("icons/start_16.png"))
        self.stop_button_u.setIcon(QtGui.QIcon("icons/stop_16.png"))
        self.pause_button_u.setIcon(QtGui.QIcon("icons/pause_16.png"))
        self.start_button_log_u.setIcon(QtGui.QIcon("icons/start_16.png"))
        self.stop_button_log_u.setIcon(QtGui.QIcon("icons/stop_16.png"))
        self.pause_button_log_u.setIcon(QtGui.QIcon("icons/pause_16.png"))
        self.paused = False
        self.started = False
        self.stopped = True
        self.timers = []
        self.gpsIndex = 0
        self.gps_direction = 1
        
        self.lcd_timer = QtCore.QTimer()
        self.lcd_timer.timeout.connect(self.update_lcd)
        self.lcd_timer.start(1000)
        
        self.gps_enable_u.setChecked(True)
        self.single_shot_enable_u.setChecked(True)
        

    def __setEventConnector(self):
        self.start_button_u.clicked.connect(self.startSim)
        self.stop_button_u.clicked.connect(self.stopSim)
        self.pause_button_u.clicked.connect(self.pauseSim)
        self.start_button_log_u.clicked.connect(self.startSim)
        self.stop_button_log_u.clicked.connect(self.stopSim)
        self.pause_button_log_u.clicked.connect(self.pauseSim)
        self.clear_button_u.clicked.connect(self.clearLog)
        self.tracker_file_button_u.clicked.connect(self.selectGPSFile)
        self.kafka_enable_button_u.clicked.connect(self.enableKafka)
        self.soap_enable_button_u.clicked.connect(self.enableSoap)
    
    def enableKafka(self):
        self.kafka_enable_button_u.setChecked(True)
        self.kafka_server_address_u.setEnabled(True)
        self.kafka_server_address_u.setCursorPosition(0)
        self.soap_enable_button_u.setChecked(False)
        self.soap_server_address_u.setEnabled(False)
        
    def enableSoap(self):
        self.soap_enable_button_u.setChecked(True)
        self.soap_server_address_u.setEnabled(True)
        self.soap_server_address_u.setCursorPosition(0)
        self.kafka_enable_button_u.setChecked(False)
        self.kafka_server_address_u.setEnabled(False)

    def getParameter(self):
        self.para ={}
        self.para["vin_prefix"] = self.vin_prefix_u.text()
        self.para["use_prefix"] = self.use_vin_prefix_u.isChecked()
        self.para["vin"] = self.vin_u.text()
        self.para["can_1_enable"] = self.can_1_enable_u.isChecked()
        self.para["can_1_interval"] = self.can_1_interval_u.text()
        self.para["can_2_enable"] = self.can_2_enable_u.isChecked()
        
        
        can_1_intv = self.can_1_interval_u.text()
        can_2_intv = self.can_2_interval_u.text()
        ad_1_intv = self.ad_1_interval_u.text()
        ad_2_intv = self.ad_2_interval_u.text()
        try:
            can_1_intv = int(can_1_intv)
            can_2_intv = int(can_2_intv)
            ad_1_intv = int(ad_1_intv)
            ad_2_intv = int(ad_2_intv)
        except Exception:
            QtGui.QMessageBox.about(self, 'Error','Interval time should be a number')
            pass

        self.para["can_1_interval"] = can_1_intv
        self.para["can_2_interval"] = can_2_intv
        self.para["ad_1_interval"] = ad_1_intv
        self.para["ad_2_interval"] = ad_2_intv

        self.para["can_1_sig_1_alg"] = self.can_1_sig_1_alg_u.currentText()
        self.para["can_1_sig_2_alg"] = self.can_1_sig_2_alg_u.currentText()
        self.para["can_1_sig_3_alg"] = self.can_1_sig_3_alg_u.currentText()
        self.para["can_2_sig_1_alg"] = self.can_2_sig_1_alg_u.currentText()
        self.para["can_2_sig_2_alg"] = self.can_2_sig_2_alg_u.currentText()
        self.para["can_2_sig_3_alg"] = self.can_2_sig_3_alg_u.currentText()
        
        self.para["ad_1_enable"] = self.ad_1_enable_u.isChecked()
        self.para["ad_2_enable"] = self.ad_2_enable_u.isChecked()
        self.para["ad_1_interval"] = self.ad_1_interval_u.text()
        self.para["ad_2_interval"] = self.ad_2_interval_u.text()

        self.para["ad_1_alg"] = self.ad_1_alg_u.currentText()
        self.para["ad_2_alg"] = self.ad_2_alg_u.currentText()
        self.para["gps_enable"] = self.gps_enable_u.isChecked()
        self.para["soap_server_address"] = self.soap_server_address_u.text()
        self.para["kafka_server_address"] = self.kafka_server_address_u.text()
        self.para["kafka_enable"] = self.kafka_enable_button_u.isChecked()
        self.para["soap_enable"] = self.soap_enable_button_u.isChecked()

        thread_num,flag = self.thread_number_u.text().toInt()

        if (flag):
            thread_num = abs(thread_num)
            if ( thread_num !=0 ):
                self.para["thread_number"]= thread_num
            else:
                self.para["thread_number"]=1
                
        else:
            self.para["thread_number"]=1

        self.thread_number_u.setText(str(self.para["thread_number"]))
       
        # No Track file, disable GPS 
        if (not self.gps_tracker_file_u.text() or str(self.gps_tracker_file_u.text()).isspace()):
            self.para["gps_enable"]=False
            self.gps_enable_u.setChecked(False)
            
        return self.para

    def selectGPSFile(self):
        fileDialog = QFileDialog()
        self.gps_tracker_file_u.setText(fileDialog.getOpenFileName())
        if (self.gps_enable_u.isChecked()):
            gps_file = unicode(self.gps_tracker_file_u.text())
            filename,suffix = os.path.splitext(gps_file)
            if (not suffix or suffix.isspace()):
                QtGui.QMessageBox.critical(self, 'Error','GPS tracker file needed !') 
                return False 
            if (suffix.lower() != ".gpx"):
                QtGui.QMessageBox.critical(self, 'Error','GPS tracker data only support gpx format') 
                return False 
           
            gpx_file = open(gps_file, 'r') 
            self.gpx = gpxpy.parse(gpx_file)
            gpx_file.close()
            self.gps_points = self.gpx.tracks[0].segments[0].points
            self.gps_points_u.display(len(self.gps_points))
            self.gps_update()
            self.gpsIndex = 0
           
    def update_lcd(self):
        self.can_counter_u.display(counter.can)
        self.ad_counter_u.display(counter.ad)
        self.gps_counter_u.display(counter.gps)
        self.can_error_counter_u.display(counter.can_error)
        self.ad_error_counter_u.display(counter.ad_error)
        self.gps_error_counter_u.display(counter.gps_error)
    
    def clean_counter(self):
        counter.ad = 0
        counter.gps = 0
        counter.can = 0
        counter.ad_error = 0
        counter.gps_error = 0
        counter.can_error = 0
    
    def clean_timers(self):
        [ timer.stop() for timer in self.timers ]
        self.timers = []


    def clean_canvas(self):
        self.can_1_sig_1_canvas.x=[]
        self.can_1_sig_1_canvas.y=[]

        self.can_1_sig_2_canvas.x=[]
        self.can_1_sig_2_canvas.y=[]

        self.can_1_sig_3_canvas.x=[]
        self.can_1_sig_3_canvas.y=[]

        self.can_2_sig_1_canvas.x=[]
        self.can_2_sig_1_canvas.y=[]

        self.can_2_sig_2_canvas.x=[]
        self.can_2_sig_2_canvas.y=[]

        self.can_2_sig_3_canvas.x=[]
        self.can_2_sig_3_canvas.y=[]

        self.ad_1_canvas.x=[]
        self.ad_1_canvas.y=[]

        self.ad_2_canvas.x=[]
        self.ad_2_canvas.y=[]
    

    def logger(self,message,time_stamp=True):
        currentDate = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")
        if (type(message) is dict):
            for key in message:
                if (time_stamp):
                    logTemplate="{0} : {1} --> {2}"
                    self.log_u.append(logTemplate.format(currentDate,key,message[key]).decode('utf-8'))
                else:
                    logTemplate="{0} --> {1}"
                    self.log_u.append(logTemplate.format(key,message[key]).decode('utf-8'))
                    
        if (type(message) is str):
            if (time_stamp):
                logTemplate="{0} : {1}"
                self.log_u.append(logTemplate.format(currentDate,message).decode('utf-8'))
            else:
                logTemplate="{0}"
                self.log_u.append(logTemplate.format(message).decode('utf-8'))
    
    def checkServerAddress(self):
        if (self.soap_enable_button_u.isChecked()):
            server_address=str(self.para["soap_server_address"])
            try:
                self.soap = Client(server_address)
                list_of_methods = [method for method in self.soap.wsdl.services[0].ports[0].methods]
                print list_of_methods
                self.logger("Check soap server connection........passed")
                return True
            except Exception as e:
                self.logger("<font color=red>Check soap server connection.......failed</font>")
                print "Create Soap instance exception:",e
                QtGui.QMessageBox.critical(self, 'Error','Connect to soap server failed...')
                return False
        elif (self.kafka_enable_button_u.isChecked()):
            server_address=str(self.para["kafka_server_address"]).split(':')
            
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
                s.connect((server_address[0],int(server_address[1])))
                s.close()
                self.kafka = KafkaClient(str(self.para["kafka_server_address"]))
                self.producer = SimpleProducer(self.kafka,async=True)
                self.logger("Check kafka server connection........passed")
                return True
            except Exception as e:
                self.logger("<font color=red>Check kafka server connection.......failed</font>")
                print "Testing Kafka server exception:",e
                QtGui.QMessageBox.critical(self, 'Error','Connect to Kafka server failed...')
                return False
        else:
            return True
    
    def startSim(self):
        self.logger("<font color=blue>----------------------Start---------------------------------</font>")
        parameters = self.getParameter()
	self.logger(parameters)

        # there have some errors in parameters
        if (not parameters):
            return
        # One step simulation 
       
        if (not self.checkServerAddress()):
            return
        
        self.started = True;
        self.start_button_u.setEnabled(False)
        self.stop_button_u.setEnabled(True)
        self.pause_button_u.setEnabled(True)

        self.start_button_log_u.setEnabled(False)
        self.stop_button_log_u.setEnabled(True)
        self.pause_button_log_u.setEnabled(True)
#        self.logger(parameters)

        if (not self.paused):
            self.clean_counter()
            self.init_alg()
            self.paused = False
            self.clean_canvas()

        self.started = True
        self.paused = False
        self.stopped = False

        if (not self.single_shot_enable_u.isChecked()):
            self.start_timer()
        else:
            self.start_single_shot_timer()
            self.start_button_u.setEnabled(True)
            self.stop_button_u.setEnabled(False)
            self.pause_button_u.setEnabled(False)

            self.start_button_log_u.setEnabled(True)
            self.stop_button_log_u.setEnabled(False)
            self.pause_button_log_u.setEnabled(False)
            self.started = False
            self.paused = True
            self.stopped = False

    
    def start_single_shot_timer(self):
        if (self.para["can_1_enable"]):
            QtCore.QTimer().singleShot(0, self.can_1_update)

        if (self.para["can_2_enable"]):
            QtCore.QTimer().singleShot(0, self.can_2_update)

            
        if (self.para["ad_1_enable"]):
            QtCore.QTimer().singleShot(0, self.ad_1_update)

        if (self.para["ad_2_enable"]):
            QtCore.QTimer().singleShot(0, self.ad_2_update)
        
        if (self.para["gps_enable"]):
            QtCore.QTimer().singleShot(0, self.gps_update)


    def start_timer(self):
        if (self.para["can_1_enable"]):
            self.can_1_timer = QtCore.QTimer()
            self.can_1_timer.timeout.connect(self.can_1_update)
            self.can_1_timer.start(int(self.para["can_1_interval"]))
            self.timers.append(self.can_1_timer)

        if (self.para["can_2_enable"]):
            self.can_2_timer = QtCore.QTimer()
            self.can_2_timer.timeout.connect(self.can_2_update)
            self.can_2_timer.start(int(self.para["can_2_interval"]))
            self.timers.append(self.can_2_timer)
            
        if (self.para["ad_1_enable"]):
            self.ad_1_timer = QtCore.QTimer()
            self.ad_1_timer.timeout.connect(self.ad_1_update)
            self.ad_1_timer.start(int(self.para["ad_1_interval"]))
            self.timers.append(self.ad_1_timer)

        if (self.para["ad_2_enable"]):
            self.ad_2_timer = QtCore.QTimer()
            self.ad_2_timer.timeout.connect(self.ad_2_update)
            self.ad_2_timer.start(int(self.para["ad_2_interval"]))
            self.timers.append(self.ad_2_timer)
        
        if (self.para["gps_enable"]):
            self.gps_timer = QtCore.QTimer()
            self.gps_timer.timeout.connect(self.gps_update)
            self.gps_timer.start(1000)
            self.timers.append(self.gps_timer)

    # Return VIN list according to thread_number and vin
    def getVIN(self):
        vin_list=[]
        vin_start = int(self.para["vin"])
        vin_stop = int(self.para["thread_number"])
        vin_prefix=str(self.para["vin_prefix"])
        
        for  x in range(vin_start,vin_start+vin_stop,1):
            vin_prefix = "%s%s"%(vin_prefix,(10-len(vin_prefix))*'0')
            vin = "%s%07d" %(vin_prefix,x)
            vin_list.append(vin)

        return vin_list
    
    def stopSim(self):
        if (self.started or self.paused):
            self.start_button_u.setEnabled(True)
            self.stop_button_u.setEnabled(False)
            self.pause_button_u.setEnabled(False)
        self.clean_timers()
        self.started = False
        self.paused = False
        self.stopped = True

    def pauseSim(self):
        if (self.started):
            self.paused = True
            self.started = False
            self.stopped = False
            self.pause_button_u.setEnabled(False)
            self.start_button_u.setEnabled(True)
            self.stop_button_u.setEnabled(True)
            self.clean_timers()

    def clearLog(self):
        self.log_u.clear()


    def init_alg(self):
        self.can_1_sig_1_alg = ALG(self.para["can_1_sig_1_alg"])
        self.can_1_sig_2_alg = ALG(self.para["can_1_sig_2_alg"])
        self.can_1_sig_3_alg = ALG(self.para["can_1_sig_3_alg"])
        self.can_2_sig_1_alg = ALG(self.para["can_2_sig_1_alg"])
        self.can_2_sig_2_alg = ALG(self.para["can_2_sig_2_alg"])
        self.can_2_sig_3_alg = ALG(self.para["can_2_sig_3_alg"])
        self.ad_1_alg = ALG(self.para["ad_1_alg"])
        self.ad_2_alg = ALG(self.para["ad_2_alg"])

        
    def can_1_update(self):
        x=time.time()
        x1,y1=self.can_1_sig_1_alg.getNext()
        self.can_1_sig_1_canvas.addPoint(x,int(y1/0.0625)*0.0625)
        x2,y2=self.can_1_sig_2_alg.getNext()
        self.can_1_sig_2_canvas.addPoint(x,int(y2/0.0625)*0.0625)
        x3,y3=self.can_1_sig_3_alg.getNext()
        self.can_1_sig_3_canvas.addPoint(x,y3)
	    #print "can_1_update start time:",time.time()*1000
        #self.logger("CAN-1 [CAN MSG 0x92] was triggered.")
        vins = self.getVIN()
        if (self.single_shot_enable_u.isChecked()):
            self.logger("<font color=red>Vechicle CNT=%d --> [CAN MSG 0x92]: v1=%r v2=%r v3=%r</font> "%(len(vins),y1,y2,y3))
            self.logger(printStr2Hex(can_1_assemble(str(vins[0]),y1,y2,y3)),time_stamp=False)

        for vin in vins:
            packet = can_1_assemble(str(vin),y1,y2,y3)
            if (self.soap_enable_button_u.isChecked()):
                send_thread = send_packet_by_soap(self.soap,packet,"CAN")
            else:
                send_thread = send_packet_by_kafka(self.producer,packet,"CAN")
            send_thread.start()
	    #print "can_1_update end time:",time.time()*1000

    def can_2_update(self):
        x1,y1=self.can_2_sig_1_alg.getNext()
        self.can_2_sig_1_canvas.addPoint(x1,y1)
        x2,y2=self.can_2_sig_2_alg.getNext()
        self.can_2_sig_2_canvas.addPoint(x2,y2)
        x3,y3=self.can_2_sig_3_alg.getNext()
        self.can_2_sig_3_canvas.addPoint(x3,y3)
        #self.logger("CAN-2 [CAN MSG 0x104] was triggered.")
       
        vins = self.getVIN()
        if (self.single_shot_enable_u.isChecked()):
            self.logger("<font color=green>Vechicle CNT=%d --> [CAN MSG 0x104]: v1=%r v2=%r v3=%r </font>"%(len(vins),y1,y2,y3))
            self.logger(printStr2Hex(can_2_assemble(str(vins[0]),y1,y2,y3)),time_stamp=False)
        for vin in vins:
            packet = can_2_assemble(str(vin),y1,y2,y3)
            if (self.soap_enable_button_u.isChecked()):
                send_thread = send_packet_by_soap(self.soap,packet,"CAN")
            else:
                send_thread = send_packet_by_kafka(self.producer,packet,"CAN")
            send_thread.start()

    def ad_1_update(self):
        x,y=self.ad_1_alg.getNext()
        self.ad_1_canvas.addPoint(x,y)

    def ad_2_update(self):
        x,y=self.ad_2_alg.getNext()
        self.ad_2_canvas.addPoint(x,y)
    
    def gps_update(self):
        if (self.gps_enable_u.isChecked()):
            self.gpsIndex+=self.gps_direction
            y = self.gps_points[self.gpsIndex].latitude
            x = self.gps_points[self.gpsIndex].longitude
            map_width=self.map_view_u.width()
            map_height=self.map_view_u.height()
            x1,y1=correct_gps(x,y)
            url='http://api.map.baidu.com/staticimage?center=%s,%s&width=%d&height=%d&zoom=14&markers=%s,%s' %(x1,y1,map_width,map_height,x1,y1)
            map_data = urllib.urlopen(url).read()
            baidu_map = QPixmap()
            baidu_map.loadFromData(map_data)

            self.map_view_u.setPixmap(baidu_map)
            self.map_view_u.show()
            
            if(self.gpsIndex == len(self.gps_points)):
                self.gps_direction=-1
            
            if (self.gpsIndex == 0):
                self.gps_direction=1
                
                          
            vins = self.getVIN()
            if (self.single_shot_enable_u.isChecked()):
                self.logger("Vechicle CNT=%d --> [GPS]: longtitude=%r latitude=%r "%(len(vins),x,y))
                self.logger(printStr2Hex(gps_assemble(str(vins[0]),x,y)),time_stamp=False)
                
            for vin in vins:
                packet = gps_assemble(str(vin),x,y)  
                if (self.soap_enable_button_u.isChecked()):
                    send_thread = send_packet_by_soap(self.soap,packet,"GPS")
                else:
                    send_thread = send_packet_by_kafka(self.producer,packet,"GPS")
                send_thread.start()
                
class send_packet_by_soap(threading.Thread):
    def __init__(self,soap,packet,type):
        threading.Thread.__init__(self)
        self.soap = soap
        self.packet = packet
        self.type = type
    
    def run(self):
        try:
            self.soap.service.uploadPacket("test","test","simulator",self.packet.encode('base64'))
            if (self.type=='GPS'):
                counter.increase_gps()
            elif (self.type == 'CAN'):
                counter.increase_can()
            elif (self.type == 'AD'):
                counter.increase_ad()
            
        except Exception as e:
            print "Soap Error",e
            if (self.type=='GPS'):
                counter.increase_gps_error()
            elif (self.type == 'CAN'):
                counter.increase_can_error()
            elif (self.type == 'AD'):
                counter.increase_ad_error()
            pass
       
class send_packet_by_kafka(threading.Thread):
    def __init__(self,producer,packet,type):
        threading.Thread.__init__(self)
        self.producer = producer
        self.packet = packet
        self.type = type
    
    def run(self):
        try:
            self.producer.send_messages(b'packet-raw', self.packet)
            
            if (self.type=='GPS'):
                counter.increase_gps()
            elif (self.type == 'CAN'):
                counter.increase_can()
            elif (self.type == 'AD'):
                counter.increase_ad()
            
        except Exception as e:
            print "Produce to Kafka Error --> ",e
            if (self.type=='GPS'):
                counter.increase_gps_error()
            elif (self.type == 'CAN'):
                counter.increase_can_error()
            elif (self.type == 'AD'):
                counter.increase_ad_error()
            pass 

if __name__ == '__main__':
    #logging.basicConfig(
    #format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
    #level=logging.DEBUG
    #)
    counter = Counter()
    app = QtGui.QApplication(sys.argv)
    mainWindow = SimWindow()
#    mainWindow.resize(1440,900)
#    mainWindow.centralWidget()
    sys.exit(app.exec_())
