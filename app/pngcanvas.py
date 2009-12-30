#!/usr/bin/env python

"""Simple PNG Canvas for Python"""
__version__ = "0.8"
__author__ = "Rui Carmo (http://the.taoofmac.com)"
__copyright__ = "CC Attribution-NonCommercial-NoDerivs 2.0 Rui Carmo"
__contributors__ = ["http://collaboa.weed.rbse.com/repository/file/branches/pgsql/lib/spark_pr.rb"], ["Eli Bendersky"]

import zlib, struct

signature = struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)

# alpha blends two colors, using the alpha given by c2
def blend(c1, c2):
  return [c1[i]*(0xFF-c2[3]) + c2[i]*c2[3] >> 8 for i in range(3)]

# calculate a new alpha given a 0-0xFF intensity
def intensity(c,i):
  return [c[0],c[1],c[2],(c[3]*i) >> 8]

# calculate perceptive grayscale value
def grayscale(c):
  return int(c[0]*0.3 + c[1]*0.59 + c[2]*0.11)

# calculate gradient colors
def gradientList(start,end,steps):
  delta = [end[i] - start[i] for i in range(4)]
  grad = []
  for i in range(steps+1):
    grad.append([start[j] + (delta[j]*i)/steps for j in range(4)])
  return grad

class PNGCanvas:
  def __init__(self, width, height,bgcolor=[0xff,0xff,0xff,0xff],color=[0,0,0,0xff]):
    self.canvas = []
    self.width = width
    self.height = height
    self.color = color #rgba
    bgcolor = bgcolor[0:3] # we don't need alpha for background
    for i in range(height):
      self.canvas.append([bgcolor] * width)

  def point(self,x,y,color=None):
    if x<0 or y<0 or x>self.width-1 or y>self.height-1: return
    if color == None: color = self.color
    self.canvas[y][x] = blend(self.canvas[y][x],color)

  def _rectHelper(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x0 > x1: x0, x1 = x1, x0
    if y0 > y1: y0, y1 = y1, y0
    return [x0,y0,x1,y1]

  def verticalGradient(self,x0,y0,x1,y1,start,end):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    grad = gradientList(start,end,y1-y0)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        self.point(x,y,grad[y-y0])

  def rectangle(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    self.polyline([[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]])

  def filledRectangle(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        self.point(x,y,self.color)

  def copyRect(self,x0,y0,x1,y1,dx,dy,destination):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        destination.canvas[dy+y-y0][dx+x-x0] = self.canvas[y][x]

  def blendRect(self,x0,y0,x1,y1,dx,dy,destination,alpha=0xff):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        rgba = self.canvas[y][x] + [alpha]
        destination.point(dx+x-x0,dy+y-y0,rgba)

  # draw a line using Xiaolin Wu's antialiasing technique
  def line(self,x0, y0, x1, y1):
    # clean params
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if y0>y1:
      y0, y1, x0, x1 = y1, y0, x1, x0
    dx = x1-x0
    if dx < 0:
      sx = -1
    else:
      sx = 1
    dx *= sx
    dy = y1-y0

    # 'easy' cases
    if dy == 0:
      for x in range(x0,x1,sx):
        self.point(x, y0)
      return
    if dx == 0:
      for y in range(y0,y1):
        self.point(x0, y)
      self.point(x1, y1)
      return
    if dx == dy:
      for x in range(x0,x1,sx):
        self.point(x, y0)
        y0 = y0 + 1
      return

    # main loop
    self.point(x0, y0)
    e_acc = 0
    if dy > dx: # vertical displacement
      e = (dx << 16) / dy
      for i in range(y0,y1-1):
        e_acc_temp, e_acc = e_acc, (e_acc + e) & 0xFFFF
        if (e_acc <= e_acc_temp):
          x0 = x0 + sx
        w = 0xFF-(e_acc >> 8)
        self.point(x0, y0, intensity(self.color,(w)))
        y0 = y0 + 1
        self.point(x0 + sx, y0, intensity(self.color,(0xFF-w)))
      self.point(x1, y1)
      return

    # horizontal displacement
    e = (dy << 16) / dx
    for i in range(x0,x1-sx,sx):
      e_acc_temp, e_acc = e_acc, (e_acc + e) & 0xFFFF
      if (e_acc <= e_acc_temp):
        y0 = y0 + 1
      w = 0xFF-(e_acc >> 8)
      self.point(x0, y0, intensity(self.color,(w)))
      x0 = x0 + sx
      self.point(x0, y0 + 1, intensity(self.color,(0xFF-w)))
    self.point(x1, y1)

  def polyline(self,arr):
    for i in range(0,len(arr)-1):
      self.line(arr[i][0],arr[i][1],arr[i+1][0], arr[i+1][1])

  def dump(self):
    raw_list = []
    for y in range(self.height):
      raw_list.append(chr(0)) # filter type 0 (None)
      for x in range(self.width):
        raw_list.append(struct.pack("!3B",*self.canvas[y][x]))
    raw_data = ''.join(raw_list)

    # 8-bit image represented as RGB tuples
    # simple transparency, alpha is pure white
    return signature + \
      self.pack_chunk('IHDR', struct.pack("!2I5B",self.width,self.height,8,2,0,0,0)) + \
      self.pack_chunk('tRNS', struct.pack("!6B",0xFF,0xFF,0xFF,0xFF,0xFF,0xFF)) + \
      self.pack_chunk('IDAT', zlib.compress(raw_data,9)) + \
      self.pack_chunk('IEND', '')

  def pack_chunk(self,tag,data):
    to_check = tag + data
    return struct.pack("!I",len(data)) + to_check + struct.pack("!I", zlib.crc32(to_check) & 0xFFFFFFFF)

  def load(self,f):
    assert f.read(8) == signature
    self.canvas=[]
    for tag, data in self.chunks(f):
      if tag == "IHDR":
        ( width,
          height,
          bitdepth,
          colortype,
          compression, filter, interlace ) = struct.unpack("!2I5B",data)
        self.width = width
        self.height = height
        if (bitdepth,colortype,compression, filter, interlace) != (8,2,0,0,0):
          raise TypeError('Unsupported PNG format')
      # we ignore tRNS because we use pure white as alpha anyway
      elif tag == 'IDAT':
        raw_data = zlib.decompress(data)
        rows = []
        i = 0
        for y in range(height):
          filtertype = ord(raw_data[i])
          i = i + 1
          cur = [ord(x) for x in raw_data[i:i+width*3]]
          if y == 0:
            rgb = self.defilter(cur,None,filtertype)
          else:
            rgb = self.defilter(cur,prev,filtertype)
          prev = cur
          i = i+width*3
          row = []
          j = 0
          for x in range(width):
            pixel = rgb[j:j+3]
            row.append(pixel)
            j = j + 3
          self.canvas.append(row)

  def defilter(self,cur,prev,filtertype,bpp=3):
    if filtertype == 0: # No filter
      return cur
    elif filtertype == 1: # Sub
      xp = 0
      for xc in range(bpp,len(cur)):
        cur[xc] = (cur[xc] + cur[xp]) % 256
        xp = xp + 1
    elif filtertype == 2: # Up
      for xc in range(len(cur)):
        cur[xc] = (cur[xc] + prev[xc]) % 256
    elif filtertype == 3: # Average
      xp = 0
      for xc in range(len(cur)):
        cur[xc] = (cur[xc] + (cur[xp] + prev[xc])/2) % 256
        xp = xp + 1
    elif filtertype == 4: # Paeth
      xp = 0
      for i in range(bpp):
        cur[i] = (cur[i] + prev[i]) % 256
      for xc in range(bpp,len(cur)):
        a = cur[xp]
        b = prev[xc]
        c = prev[xp]
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
          value = a
        elif pb <= pc:
          value = b
        else:
          value = c
        cur[xc] = (cur[xc] + value) % 256
        xp = xp + 1
    else:
      raise TypeError('Unrecognized scanline filter type')
    return cur

  def chunks(self,f):
    while 1:
      try:
        length = struct.unpack("!I",f.read(4))[0]
        tag = f.read(4)
        data = f.read(length)
        crc = struct.unpack("!i",f.read(4))[0]
      except:
        return
      if zlib.crc32(tag + data) != crc:
        raise IOError
      yield [tag,data]

if __name__ == '__main__':
  width = 128
  height = 64
  print "Creating Canvas..."
  c = PNGCanvas(width,height)
  c.color = [0xff,0,0,0xff]
  c.rectangle(0,0,width-1,height-1)
  print "Generating Gradient..."
  c.verticalGradient(1,1,width-2, height-2,[0xff,0,0,0xff],[0x20,0,0xff,0x80])
  print "Drawing Lines..."
  c.color = [0,0,0,0xff]
  c.line(0,0,width-1,height-1)
  c.line(0,0,width/2,height-1)
  c.line(0,0,width-1,height/2)
  # Copy Rect to Self
  print "Copy Rect"
  c.copyRect(1,1,width/2-1,height/2-1,0,height/2,c)
  # Blend Rect to Self
  print "Blend Rect"
  c.blendRect(1,1,width/2-1,height/2-1,width/2,0,c)
  # Write test
  print "Writing to file..."
  f = open("test.png", "wb")
  f.write(c.dump())
  f.close()
  # Read test
  print "Reading from file..."
  f = open("test.png", "rb")
  c.load(f)
  f.close()
  # Write back
  print "Writing to new file..."
  f = open("recycle.png","wb")
  f.write(c.dump())
  f.close()
