#RTP packetizer  for uncompressed video

#Y4M reader class from https://github.com/amaslenn/Y4M-Reader 
class Y4M_reader():
    
    def __init__(self):
        self.init_ok = False
        self.in_file = open("/Users/chris/Desktop/thesis/50_fps_uncomp.y4m", "rb")
        self.width, self.height = 0, 0
        self.framerate    = 0.0     
        self.aspect_ratio = 0.0
        self.color_space  = ''
        self.scan_type    = ''
        self.comment      = ''
        print("reader init done")
        
        
    
    def _get_value(self):
        val = ''
        tmp = (self.in_file.read(1))
        #reads a byte of the y4m header and checks it is not space or new line character
        #if byte is space or new line, entire value has been read
        while tmp != b' ' and tmp != b"\n":
            val += (tmp.decode('utf-8'))
            tmp = self.in_file.read(1)
        print(val)
        return str(val)


    def init(self, filename):
        try:
            self.in_file = open(filename, 'rb')
        except IOError as e:
            init_ok = False
            print('Cannot open file `' + filename + '\': ' + str(e))
            return 1

        # check beginning of the Y4M file
        data = self.in_file.read(10)    # YUV4MPEG2 + " "
        if data != b'YUV4MPEG2 ':
            init_ok = False
            print(data)
            return 2

        self.init_ok = True
        

        #peeks 5 byte ahead in y4m file for FRAME header
        #while not frame header, processes the y4m file header elements
        while self.in_file.peek(5) != b'FRAME':
            data = self.in_file.read(1)
            if data == b'W':
                self.width = int(self._get_value())
            elif data == b'H':
                self.height = int(self._get_value())
            elif data == b'F':   # framerate
                data = self._get_value()
                numerator, denominator = data.split(':')
                self.framerate = float(numerator) / float(denominator)
            elif data == b'I':   # scan type
                data = self._get_value()
                if data == b'p':
                    self.scan_type = 'progressive'
                elif data == b't':
                    self.scan_type = 'tff'
                elif data == b'b':
                    self.scan_type = 'bff'
                else:
                    self.scan_type = 'mixed'
            elif data == b'A':   # aspect ratio
                self.aspect_ratio = self._get_value()
            elif data == b'C':   # color space
                self.color_space = self._get_value()
            elif data == b'X': #comments
                self.comment = self._get_value()
                break
            else:
                print('Unknown parameter: `' + data.decode('utf-8') + '\'')
                break
        
        #parsing header done
        
        # check mandatory parameters
        if not self.width or not self.height or not self.framerate:
            self.init_ok = False
            return 2


        print ('width        =', self.width)
        print ('height       =', self.height)
        print ('framerate    =', self.framerate)
        print ('scan_type    =', self.scan_type)
        print ('aspect_ratio =', self.aspect_ratio)
        print ('color_space  =', self.color_space)
        print('comment       =', self.comment)

        return 0



    def get_next_frame(self):
        if not self.init_ok:
            return (3, '')

        #reads FRAME header and the space character, total 6 bytes
        data = self.in_file.read(6)
        if len(data) < 6:
            return (4, '')
        
        

        #y4m frame header parameters not supported, not needed in use case
        if data != b"FRAME\n":
            
            return (2, '')

        #only supports 422p10 video
        #size of frame in bytes is width * height * (1 full luminance + 2 half chroma) * 2 bytes per value (10 bits in 2 bytes)
        if (self.color_space == '422p10'):
            size = self.width * self.height * 2 * 2
        frame_data = self.in_file.read(size)

        err = 0
        if len(frame_data) < size:
            err = 5

        return (err, frame_data)


def pgroup_creator ( y_frame: bytes, u_frame: bytes, v_frame: bytes, y_second_pixel):
    #takes 2 bytes per sample value, 4 samples in one p-group, big endian coding
    result = bytearray(5)

    #first byte of result = 8Bit of u_frame
    result[0] = u_frame[0]
    
    #second byte = 2Bit of u_frame + 6Bit y_0
    result[1] = ((u_frame[1] >> 6 & 0b11) << 6) | ((y_frame[0] >> 2) & 0b111111)

    #third byte = 4Bit of y_0 + 4 Bit of v_frame
    result[2] = (y_frame[1]>>4 & 0b1111) << 4 | (v_frame[0] >>4  & 0b1111) 
    
    #fourth byte = 6 bit of v_frame + 2bit of y_1
    result[3] = ((v_frame[0] & 0b1111) << 4 ) | ((v_frame[1] >> 6 & 0b11) << 2) | (y_second_pixel[0] >> 6 & 0b11)

    #fifth byte = 8 bit of y_1
    result[4] = (y_second_pixel[0] & 0b00111111 ) << 2 | y_second_pixel[1] >> 6 & 0b11
    
    return result


def pgroup_creator_little ( y_frame: bytes, u_frame: bytes, v_frame: bytes, y_second_pixel):
    #same as pgroup_creator, except for little endian coded values
    result = bytearray(5)

    #first byte of result = 8Bit of u_frame
    result[0] = u_frame[1] << 6 & 0b11000000 | u_frame[0] >> 2 & 0b00111111
    
    #second byte = 2Bit of u_frame + 6Bit y_0
    result[1] = (u_frame[0] << 6 & 0b11000000) | ((y_frame[1] << 4) & 0b00110000) | y_frame[0] >> 4 & 0b00001111
    
    #third byte = 4Bit of y_0 + 4 Bit of v_frame
    result[2] = y_frame[0] << 4 & 0b11110000 |(v_frame[1] <<2  & 0b00001100) | v_frame[0] >> 6 & 0b00000011 
    
    #fourth byte = 6 bit of v_frame + 2bit of y_1
    result[3] = ((v_frame[0] << 2 & 0b11111100) ) | (y_second_pixel[1] )
    
    #fifth byte = 8 bit of y_1
    result[4] = y_second_pixel[0] 
    
    return result




def sample_row_data_header(length: bytes, row_num: bytes, offset: bytes, cont: bytes):
    #creates the sample row data header with length of data, line number, offset of beginning of data from start of line and cont bit for multiple lines in one packet
    result = bytearray(6)
    
    result = (length << 32) | (row_num) << 16 | offset
    
    if cont == 1:
        result = result | (cont << 15)
    
    return result


def frame_to_payload_and_send(frame: bytes, sequence_number : int, timestamp: int):
    #takes one frame and packetizes into binary file, closes the binary file after each frame to make sure data is saved
    
    #open binary file to save packet into
    file_binary_packets = open('50_fps_packets_with_padding_little_corrected.bin', 'ab')
    
    #advance the timestamp of the packet and loop once the 32 bit are full
    timestamp = timestamp + 1800
    if timestamp > 4294967295:
        timestamp = timestamp - 4294967295
    
    #possible max payload is 1386, UDP packet should have 1400 byte total payload, minus 12 byte rtp header, minus 2 byte for extended sedquence number
    #after those need srd headers with 6 bytes and payload
    
    #for slicing the frame bytes into the planes
    frame_half = int((len(frame)/2))
    frame_quarter = int((len(frame)/4))
    
    y_plane = bytearray(frame[:frame_half])
    
    u_plane = bytearray(frame[frame_half: (frame_half + frame_quarter)])
    
    v_plane = bytearray(frame[frame_half + frame_quarter:])
    
    #start packets at line 0 and offset 0 (counting from top left of a picture)
    row_number = 0
    row_offset = 0
    
    #marker for end of frame
    marker = 0
    
    #loop over y sample plane until done
    while len(y_plane) > 0:
        
        #possibly up to two srd headers with 6 byte each
        payload_bytes_left = 1374
        
        #each pgroup contains 2 y samples, a row of 1920 values gets checked against 2*274 samples for packetizing

        #current row has more than 548 y samples left
        if (1920 - row_offset) > 548:
            
            packet = bytearray()
            #Amount of pgroups that fit in a Packet (pgroup is 5 byte for 10bit 422)
            #1374 / 5 = 274 whole proups
            pgroup_amount =   int(payload_bytes_left / 5)
            
            #print("pgroup_amount" + str(pgroup_amount))
            

            #take samples needed from each plane and delete from the plane
            y_slice = y_plane[0:pgroup_amount*2*2]
            u_slice = u_plane[0:pgroup_amount*2]
            v_slice = v_plane[0:pgroup_amount*2]
            
            del(y_plane[0:pgroup_amount*2*2])
            del(u_plane[0:pgroup_amount*2])
            del(v_plane[0:pgroup_amount*2])
            
            
            #print("row_offset " + str(row_offset))
            
            #check for end of frame
            if len(y_plane) <= 0:
                marker = 1
            
            line_end = 0
            
            #create payload
            payload = slices_to_payload(y_slice, u_slice, v_slice)
            
            length = len(payload)
            #create srd header
            srd_header = sample_row_data_header(length, row_number, row_offset, line_end)
            
            rtp_header, sequence_number, sequence_upper16_bit = rtp_header_bytes(marker, sequence_number, timestamp)
            
            #assemble the packet, by adding rtp_header, sequence number, srd header and payload
            
            packet += rtp_header
            packet += sequence_upper16_bit
            packet += int(srd_header).to_bytes(6)
            packet+= payload
            
            #add 10 bytes of padding to make the packet 1400 byte long
            padding = 10
            padding_bytes = padding.to_bytes(10)
            
            packet += padding_bytes

            #write to file
            file_binary_packets.write(packet)
            
            #increase row offset by pgroup amount * 2 for used up y samples
            row_offset += (pgroup_amount*2)

            
        #current row has less than 548 y samples left, second row gets started in the packet
        if (1920 - row_offset) < 548:
            
            packet = bytearray()
            
            #remaining samples until end of line
            end_of_line_extractor = int(1920 - row_offset)
            
            #take samples until line end
            y_slice = y_plane[0:end_of_line_extractor*2]
            u_slice = u_plane[0:end_of_line_extractor]
            v_slice = v_plane[0:end_of_line_extractor]
            
            del(y_plane[0:end_of_line_extractor*2])
            del(u_plane[0:end_of_line_extractor])
            del(v_plane[0:end_of_line_extractor])
            
            line_end = 1
            
            #create payload for the first line
            payload_first_line = slices_to_payload(y_slice, u_slice, v_slice)
            
            length = len(payload_first_line)
            
            #srd header for end of the first line in the packet
            srd_header_first_line = sample_row_data_header(length, row_number, row_offset, line_end)

            #increase line number and start new line at offset 0
            row_number += 1
            row_offset = 0
            
            #calculate how many bytes still fit into the packet
            new_line_start_amount = pgroup_amount*2 - end_of_line_extractor
            
            #start taking bytes from the next line 
            y_slice_next_line = y_plane[0:new_line_start_amount*2]
            u_slice_next_line = u_plane[0:new_line_start_amount]
            v_slice_next_line = v_plane[0:new_line_start_amount]
            
            del(y_plane[0:new_line_start_amount*2])
            del(u_plane[0:new_line_start_amount])
            del(v_plane[0:new_line_start_amount])
            
            line_end = 0
            
            #check for frame end
            if len(y_plane) <= 0:
                marker = 1
            
            rtp_header, sequence_number, sequence_upper16_bit = rtp_header_bytes(marker, sequence_number, timestamp)
            
            packet += rtp_header
            packet += sequence_upper16_bit
            packet += int(srd_header_first_line).to_bytes(6)
            
            #create payload of the second line in the packet and corresponding srd header
            if len(y_slice_next_line) > 0:
                payload_second_line = slices_to_payload(y_slice_next_line, u_slice_next_line, v_slice_next_line)
                
                length = len(payload_second_line)
                #length =1
                srd_header_second_line = sample_row_data_header(length, row_number, row_offset, line_end)
                
                packet += int(srd_header_second_line).to_bytes(6)
                packet += payload_first_line
                packet += payload_second_line
            else:
                packet += payload_first_line
            
            #add padding to make 1400 byte long packet
            if marker == 0:

                padding = 4
                padding_bytes = padding.to_bytes(4)
                packet+= padding_bytes
            else:
                
                padding = 90
                padding_bytes = padding.to_bytes(90)
                packet+= padding_bytes
                
            file_binary_packets.write(packet)
            
            #add offset
            row_offset += new_line_start_amount
            
        #exactly 548 y samples left in line
        #fits perfectly into one packet
        if ((1920 - row_offset) == 548):
            
            packet = bytearray()
            
            y_slice = y_plane[0:548*2]
            u_slice = u_plane[0:pgroup_amount*2]
            v_slice = v_plane[0:pgroup_amount*2]
            
            line_end = 0
            
            del(y_plane[0:548*2])
            del(u_plane[0:pgroup_amount*2])
            del(v_plane[0:pgroup_amount*2])
            
            #check frame end
            if len(y_plane) <= 0:
                marker = 1
            
            payload = slices_to_payload(y_slice, u_slice, v_slice)
            
            length = len(payload)
            
            srd_header = sample_row_data_header(length, row_number, row_offset, line_end)
            
            rtp_header, sequence_number, sequence_upper16_bit = rtp_header_bytes(marker, sequence_number, timestamp)
            
            packet += rtp_header
            packet += sequence_upper16_bit
            packet += int(srd_header).to_bytes(6)
            packet+= payload
            #add padding
            padding = 10
            padding_bytes = padding.to_bytes(10)
            packet+= padding_bytes
            
            file_binary_packets.write(packet)
            
            #reset offset, increase number
            row_offset = 0
            row_number += 1
            
        

    #close binary file
    file_binary_packets.close()
    
    
    return timestamp, sequence_number


def slices_to_payload(y_slice, u_slice, v_slice):
    #take the slices of data and creates the payload
    payload = bytearray()
    
    while len(y_slice) > 0:
        
        #creating pgroup bytes by slicing of 2 bytes per sample
        
        y_0 = y_slice[0:2]
        del(y_slice[0:2])
        y_1 = y_slice[0:2]
        del(y_slice[0:2])
        u = u_slice[0:2]
        del(u_slice[0:2])
        v = v_slice[0:2]
        del[v_slice[0:2]]
        
        #samples to pgroup
        pgroup = pgroup_creator_little(y_0, u, v, y_1)
        
        #add to payload
        payload += pgroup
        
    
    return payload

def rtp_header_bytes(marker, sequence_number: int, timestamp: int):
    #create the rtp header with sequence number and timestamp
    rtp_header = bytearray(12)
    
    sequence_upper_16 = bytearray(2)
    
    #version and padding
    rtp_header[0] = 0b10100000
    
    #marker and payload type 96 dynamic
    if marker == 1:
        rtp_header[1] = 0b11100000
    else:
        rtp_header[1] = 0b01100000
    
    #sequence number sepeartes into lower 16bit in header and upper 16bit in payload
    #loop when bits are full
    if sequence_number == 4294967295:
        sequence_number = 0
    else:
        sequence_number += 1
    
    sequence_number_bytes = sequence_number.to_bytes(4)
    
    #sequence in header
    rtp_header[2] = sequence_number_bytes[2]
    rtp_header[3] = sequence_number_bytes[3]
    
    #extended seq in first 2 bytes of payload
    sequence_upper_16[0] = sequence_number_bytes[0]
    sequence_upper_16[1] = sequence_number_bytes[1]
    
    #timestamp
    timestamp_bytes = timestamp.to_bytes(4)
    
    rtp_header[4] = timestamp_bytes[0]
    rtp_header[5] = timestamp_bytes[1]
    rtp_header[6] = timestamp_bytes[2]
    rtp_header[7] = timestamp_bytes[3]
    
    #ssrc just some random values
    rtp_header[8] = 0b10101010
    rtp_header[9] = 0b10101010
    rtp_header[10] = 0b10101010
    rtp_header[11] = 0b10101010

    return rtp_header, sequence_number, sequence_upper_16


if __name__ == '__main__':
    
    #filename of source y4m file
    filename = "./path_to_/uncompressed.y4m"
    
    #create y4m reader
    reader = Y4M_reader()
    
    print(reader.in_file)
    
    #init the reader
    open_ok_check = reader.init(filename)
    
    print(open_ok_check)
    print(reader.init_ok)
    print(reader.in_file)
    
    err, nframes = 0, 0
    print("after init etc")
    
    #set values for sequence number start and timestamp start
    temp = 1000
    temp_sequence = 1234567
    
    #read all frames from y4m file and packetize
    while not err:
        (err, frame) = reader.get_next_frame()
#        print('Err:', err, '-- frame_size:', len(frame))
        if not err:
            nframes += 1
        
        temp, temp_sequence = frame_to_payload_and_send(frame, temp_sequence, temp)
        
        if nframes == 1:
            tempframe = frame
            
            
        print('nframes:', nframes)
