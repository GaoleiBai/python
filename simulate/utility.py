def printStr2Hex(s):
    tpe = "0x{:02x} "
    output_string="\n"+"-"*60+"\n"
    output_string+=" "*20+"length="+str(len(s))
    output_string+="\n"+"-"*60+"\n"
    for i in range(1,len(s)+1,1):
        output_string+=tpe.format(ord(s[i-1]))
        if (i % 8 == 0):
            output_string+=" "*4+"|"
            for indx in range(i-8,i,1):
                if (ord(s[indx])>128 or ord(s[indx])==0 or ord(s[indx]) == 32):
                    output_string+="."
                else:
                    output_string+=s[indx]
            output_string+="\n"
            
    align = 5*8 - i%8*5
    output_string+="-"*align
    output_string+="-"*4+"|"
    for indx in range(i-i%8,i,1):
                if (ord(s[indx])>128 or ord(s[indx])==0 or ord(s[indx]) == 32):
                    output_string+="."
                else:
                    output_string+=s[indx]

    output_string+="\n"
    return output_string
