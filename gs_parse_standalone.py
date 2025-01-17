import struct, time

_SCALAR=8000/(2**15)
cmd=None
sats = {
    0x3A:'littlefoot',
    0x3B:'petrie',
    0x3C:'cera'}


msg_cnt=1
class check_msg:
    mission_phase = ['init','cruise','late','experimental','na','na','shutdown']
    raw=bytearray(41)
    view = memoryview(raw)

cmsg = check_msg()

def parse_beacon(beacon):
    if not isinstance(beacon,bytes):
        raise TypeError('beacon packet must be of type bytes')
    m=beacon
    if m[1] in sats:
        cmsg.view[:]=m[4:]
        phase = cmsg.view[16]>>5
        flags = '{:0>8}'.format(bin(cmsg.view[16] & 0x1F)[2:])
        flags = [int(i) for i in reversed(flags)]
        flags2 = '{:0>8}'.format(bin(cmsg.view[15] & 0x0F)[2:])
        flags2 = [int(i) for i in reversed(flags2)]
        gyro=[]
        for g in (cmsg.view[17],cmsg.view[18],cmsg.view[19]):
            g = (g-128)*0.234375
            gyro.append(g)


        print(msg_cnt,end=' ')
        print('heard from {}:\n\t Packet: {}\n'.format(sats[m[1]],m))
        print('{:>23}: {}s'.format('SC Time',int.from_bytes(cmsg.view[1:6],'big')/1000))
        print('{:>23}: {}%'.format('Vbatt',         cmsg.view[20]))
        print('{:>23}: {}'.format('Boot Count',     cmsg.view[0]))
        print('{:>23}: {}'.format('VBus Resets',    cmsg.view[6]))
        print('{:>23}: {}'.format('State Errors',   cmsg.view[7]))
        print('{:>23}: {}'.format('Time Rollovers', cmsg.view[8]))
        print('{:>23}: {}'.format('Timeouts',       cmsg.view[9]))
        print('{:>23}: {}'.format('GS Messages',    cmsg.view[10]))
        print('{:>23}: {}dBm'.format('Last GS RSSI',cmsg.view[37]-137))
        print('{:>23}: {}mA'.format('Solar Chrging',cmsg.view[11]*2 if flags[1] else 0))
        print('{:>23}: {}'.format('UHF CRC Errors', cmsg.view[39]))
        print('{:>23}: {}'.format('Downlink Count', cmsg.view[38]))
        print('{:>23}: X:{} Y:{} Z:{} deg/s'.format('Gyro',*gyro))
        print('{:>23}: {}:{}'.format('Mission Phase',phase,cmsg.mission_phase[phase]))

        # NVM
        print('\tState Errors:')
        print('\t  └──{:<10}: {}   {:<10}: {}'.format(
                'Discovery',cmsg.view[12]>>4,'Xlink',(cmsg.view[12] & 0xF)))
        print('\t  └──{:<10}: {}   {:<10}: {}'.format(
                'Idle',cmsg.view[13]>>4,'Beacon',(cmsg.view[13] & 0xF)))
        print('\t  └──{:<10}: {}   {:<10}: {}   {:<10}: {}'.format(
                'Rad',cmsg.view[14]>>4,'Downlink',(cmsg.view[14] & 0xF),'Range',cmsg.view[15]>>4))

        # NVM flag byte
        print('\tFlags:')
        print('\t  └──{:>13} {:<3}  {:>16} {:<3}  {:>15} {}'.format(
            'low battery?',     'yes' if flags[0] else 'no',
            'lowbatt timeout?', 'yes' if flags[4] else 'no',
            'solar chrging?',   'yes' if flags[1] else 'no',))
        print('\t  └──{:>13} {:<3}  {:>16} {:<3}  {:>15} {}'.format(
            'gps on?',      'yes' if flags[2]  else 'no',
            'gps fix?',     'yes' if flags2[0] else 'no',
            'mesh leader?', 'yes' if flags[3]  else 'no'))


        # Data Files
        print('\tData Files')
        print('\t  └──{:>5}: {}'.format('Rad',int.from_bytes(cmsg.view[21:23],'big')))
        print('\t  └──{:>5}: {}'.format('Range',int.from_bytes(cmsg.view[23:25],'big')))
        print('\t  └──{:>5}: {}'.format('GPS',int.from_bytes(cmsg.view[25:27],'big')))

        # Data Summary
        print('\tData Summary')
        if cmsg.view[27] == 82: # b'R'
            # --- Rad Summary ---
            print('\t  └──Radiation:')
            r1 = 2.5-(int.from_bytes(cmsg.view[28:31],'big')*1.49012e-07)
            rt = int.from_bytes(cmsg.view[31:34],'big')*1.49012e-07*1000
            rt = (-1*((129.00-rt)*0.403)+25)
            r2 = 2.5-(int.from_bytes(cmsg.view[34:37],'big')*1.49012e-07)
            print('\t\t  └──R1:{}V, Temperature:{}C, R2:{}V'.format(r1,rt,r2))

        elif cmsg.view[27] in (0x3A,0x3B,0x3C):
            # --- Range Summary ---
            print('\t  └──Range w/ {}:'.format(sats[cmsg.view[27]]))
            print('\t\t  └──Good:{}, Bad:{}, Last Range:{}, EFE:{}'.format(
                            int.from_bytes(cmsg.view[28:30],'big'),cmsg.view[30],
                            int.from_bytes(cmsg.view[31:34],'big'),
                            int.from_bytes(cmsg.view[34:37],'big')))

        elif cmsg.view[27] in (0xFA,0xFB,0xFC):
            # --- Xlink Summary ---
            s_id = (cmsg.view[27] & 0x0F) | 0x30
            print('\t  └──Xlink w/ ({}){}:'.format(hex(s_id),sats[s_id]))
            print('\t\t  └──Good-UHF:{}, Good-SBand:{}, Last Xlink Time:{}, UHF-RSSI:{}dBm, SBand-RSSI:{}dBm'.format(
                            cmsg.view[28],cmsg.view[29],
                            int.from_bytes(cmsg.view[30:35],'big')/1000,
                            cmsg.view[35]-137,
                            -1*cmsg.view[36]/2))

        elif cmsg.view[27] == 0xA8:
            # --- GPS Summary ---
            print('\t  └──GPS info:')
            _time = int.from_bytes(cmsg.view[28:31],'big')
            _ecef = struct.unpack('>HHH',cmsg.view[31:37])
            print('\t\t  └──Time of the week:{}s, ECEF(X):{}km, ECEF(Y):{}km, ECEF(Z):{}km'.format(
                _time,
                (_ecef[0]-32768)*_SCALAR,
                (_ecef[1]-32768)*_SCALAR,
                (_ecef[2]-32768)*_SCALAR,
                ))


        # Check CRC
        c=0
        for i in cmsg.view[:-1]:
            c^=i
        print('   {}:{} valid? {}'.format('CRC',hex(c),bool(c==cmsg.view[-1])))
