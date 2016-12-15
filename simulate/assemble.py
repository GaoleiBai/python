from bitstring import BitArray
import time
from utils import printStr2Hex

def getTime():
    now = time.time()
    seconds = int(now)
    msec = int((now - seconds)*1000)
   
    #packetTime= "%s%s"%(struct.pack("<I",seconds),struct.pack("<H",msec))
    #print "".join("{:02x}".format(ord(c)) for c in a) 
    return (seconds,msec)



def can_1_assemble(vin,v1,v2,v3):
    channel=BitArray(uint=1,length=8)  #Channel = 1  1-bytes
    seconds,msec=getTime()
    can_1_segment_type = 66    #0x92 CAN/UPLOAD
    v = BitArray(bytes=vin,length=17*8)      # VIN, 17-bytes
    ts = BitArray(uintbe=seconds,length=4*8) # seconds, little-endian   4-bytes
    tms = BitArray(uintbe=msec,length=2*8)    # millisecond big-endian   2-bytes
    st = BitArray(uintbe=can_1_segment_type,length=1*8)  # Segment Type=0x42  1-bytes
    can_id = BitArray(uintbe=146,length=4*8)  #can ID=0x92(146D)   4-bytes
    dlc=BitArray(uintbe=8,length=1*8)  #DLC=8  1-bytes  
    d0 = BitArray(12)
    d1 = BitArray(uintbe=int(v1/0.0625),length=2*8)  #Start=12 length=16 WheelSpeed_FL 2-bytes Factor=0.0625
    d2 = BitArray(uintbe=int(v2/0.0625),length=2*8)  #Start=28 length=16 WheelSpeed_FR 2-bytes  Factor=0.0625
    d3 = BitArray(4)
    d4 = BitArray(uint=int(v3),length=8)  # Start=48 length=8 BrackPressure
    de = BitArray(8)
    data = de+d4+d3+d2+d1+d0    # assemble it in reversed order and reverse it to normal later
    data0= BitArray(bytes=data.bytes[::-1],length=len(data))
    
    packet = v+ts+tms+st+channel+ts+tms+can_id+dlc+data0
    return packet.bytes

def can_2_assemble(vin,v1,v2,v3):
    seconds,msec=getTime()
    channel=BitArray(uint=1,length=8)  #Channel = 1  1-bytes
    can_2_segment_type = 66    #0x42 CAN/UPLOAD
    v = BitArray(bytes=vin,length=17*8)      # VIN, 17-bytes
    ts = BitArray(uintbe=seconds,length=4*8) # seconds, little-endian   4-bytes
    tms = BitArray(uintbe=msec,length=2*8)    # millisecond big-endian   2-bytes
    st = BitArray(uintbe=can_2_segment_type,length=1*8)  # Segment Type=0x42  1-bytes
    can_id = BitArray(uintbe=260,length=4*8)  #can ID=0x104(260D)   4-bytes
    dlc=BitArray(uintbe=2,length=1*8)  #DLC=2  1-bytes  
    d0 = BitArray(8)
    d1 = BitArray(uint=v1,length=2)
    d2 = BitArray(uint=v2,length=2)
    d3 = BitArray(uint=v3,length=2)
    de = BitArray(2)
    data = de+d3+d2+d1+d0       # Data 2-bytes
    data0= BitArray(bytes=data.bytes[::-1],length=len(data))  # assemble it in reversed order and reverse it to normal later
    
    packet = v+ts+tms+st+channel+ts+tms+can_id+dlc+data0
    return packet.bytes

def gps_assemble(vin,longtitude,latitude):
    seconds,msec=getTime()
    gps_segment_type = 68    #0x44 GPS/UPLOAD
    v = BitArray(bytes=vin,length=17*8)      # VIN, 17-bytes
    ts = BitArray(uintbe=seconds,length=4*8) # seconds, little-endian   4-bytes
    tms = BitArray(uintbe=msec,length=2*8)    # millisecond big-endian   2-bytes 
    st = BitArray(uint=gps_segment_type,length=1*8)  # Segment Type=0x42  1-bytes
    #Bit 0-7 GPS status 0x00 
    s=BitArray(8)
    s[0]=0
    s[1]=0
    s[2]=0
    x=BitArray(uintbe=int(float(longtitude)*1000000) ,length=4*8)  #longtitude  4-bytes factor=1E6
    y=BitArray(uintbe=int(float(latitude)*1000000) ,length=4*8) #latitude  4-bytes factor=1E6
    speed=BitArray(uint=0,length=2*8)
    direction=BitArray(uint=0,length=2*8)
    evelation=BitArray(uint=0,length=2*8)
    data=s+x+y+speed+direction+evelation

    
    packet=v+ts+tms+st+data
    return packet.bytes

def ad_assemble(channel,vin,v):    
    seconds,msec=getTime()
    ad_segment_type = 67    #0x43 GPS/UPLOAD
    channel=BitArray(uint=channel,length=8)  #Channel = 1  1-bytes
    v = BitArray(bytes=vin,length=17*8)      # VIN, 17-bytes
    ts = BitArray(uintbe=seconds,length=4*8) # seconds, little-endian   4-bytes
    tms = BitArray(uintbe=msec,length=2*8)    # millisecond big-endian   2-bytes 
    st = BitArray(uint=ad_segment_type,length=1*8)  # Segment Type=0x42  1-bytes
    data=BitArray(floatbe=v,length=4*8)
    
    packet = v+ts+tms+st+channel+ts+tms+data
    return packet.bytes

if __name__ == '__main__':
    print printStr2Hex(can_1_assemble('PLV00000000000123',0.375,560,3))
