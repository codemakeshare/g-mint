from numpy import *
from geometry import *
import traceback

class GCommand:
    def __init__(self, command="", position=None, rotation=None, feedrate=None, rapid=False,
                 control_point=True, line_number=0,
                 axis_mapping = ["X", "Y", "Z"], axis_scaling = [1.0, 1.0, 1,0], rot_axis_mapping=["A", "B", "C"]):
        self.command = command
        self.axis_mapping = axis_mapping
        self.axis_scaling = axis_scaling
        self.rot_axis_mapping=  rot_axis_mapping
        self.control_point = control_point
        self.feedrate = feedrate
        self.rapid = rapid
        self.position = position
        self.rotation=rotation
        self.line_number=line_number
        self.interpolated=False

    def to_output(self):
        return "%s" % (self.command)

    def parse_line(self, input_line):
        self.command = line

    def interpolate_to_points(self, current_pos):
        return []


class GPoint(GCommand):
    def __init__(self, inside_model=True, control_point=False,
                 in_contact=True, interpolated = False, order=0, dist_from_model=None, **kwargs):
        GCommand.__init__(self,  **kwargs)
        self.control_point = control_point
        self.inside_model = inside_model
        self.in_contact = in_contact
        self.dist_from_model = dist_from_model
        self.current_system_feedrate = None
        self.interpolated=interpolated
        self.order = order  # indicates order of cascaded pocket paths - 0 is innermost (starting) path
        self.gmode = "G1"
        if self.rapid:
            self.gmode = "G0"

    def z_to_output(self):

        if self.position is not None:
            self.command = self.axis_mapping[2]+"%f " % (self.position[2])
        if self.feedrate != None:
            self.command = "%sF%f" % (self.command, self.feedrate)
        return self.command

    def to_output(self):
        am = self.axis_mapping
        ram = self.rot_axis_mapping
        if not self.control_point:
            self.command = "%s%f %s%f %s%f " % (am[0], self.position[0]*self.axis_scaling[0], am[1], self.position[1]*self.axis_scaling[1], am[2], self.position[2]*self.axis_scaling[2])
            if self.rotation is not None:
                self.command += "%s%f %s%f %s%f " % (ram[0], self.rotation[0], ram[1], self.rotation[1], ram[2], self.rotation[2])
        # if self.feedrate!=None:
        #    self.command="%sF%f"%(self.command,  self.feedrate)
        return self.command

    def interpolate_to_points(self, current_pos):
        return[(GPoint(position=self.position, rotation = self.rotation, feedrate=self.feedrate, rapid=self.rapid, line_number=self.line_number))]

class GArc(GPoint):
    def __init__(self, ij=None, arcdir=None, control_point=False, **kwargs):
        GPoint.__init__(self, **kwargs)
        self.control_point = control_point
        self.ij = ij
        if arcdir is None:
            print("Error: undefined arc direction!")
        self.arcdir = arcdir
        self.gmode = "G"+str(self.arcdir)

    def z_to_output(self):
        am = self.axis_mapping
        if self.position is not None:
            self.command = "%s%f " % (am[2], self.position[2])
        if self.feedrate != None:
            self.command = "%sF%f" % (self.command, self.feedrate)
        return self.command

    def to_output(self, to_points=False):
        am = self.axis_mapping
        if not self.control_point:
            self.command = "%s%f %s%f %s%f I%f J%f " % (am[0], self.position[0]*self.axis_scaling[0], am[1], self.position[1]*self.axis_scaling[1], am[2], self.position[2]*self.axis_scaling[2], self.ij[0], self.ij[1])
        # if self.feedrate!=None:
        #    self.command="%sF%f"%(self.command,  self.feedrate)
        return self.command

    def interpolate_to_points(self, current_pos):
        arc_start = current_pos
        path=[]
        #print(arc_start, self.ij, self.position)
        center = [arc_start[0] + self.ij[0], arc_start[1] + self.ij[1], self.position[2]]
        start_angle = full_angle2d([arc_start[0] - center[0], arc_start[1] - center[1]], [1, 0])
        end_angle = full_angle2d([self.position[0] - center[0], self.position[1] - center[1]], [1, 0])
        angle_step = 0.05

        angle = start_angle
        radius = dist([center[0], center[1]], [arc_start[0], arc_start[1]])
        radius2 = dist([center[0], center[1]], [self.position[0], self.position[1]])

        if abs(radius-radius2)>0.01:
            print("radius mismatch:", radius, radius2)

        if int(self.arcdir) == 3:
            print(int(self.arcdir))
            while end_angle > start_angle:
                end_angle -= 2.0 * PI
            while angle > end_angle:
                path.append(
                    GPoint(position=[center[0] + radius * cos(angle), center[1] - radius * sin(angle),
                                     self.position[2]], feedrate=self.feedrate, rapid=self.rapid, interpolated=True, line_number=self.line_number));
                angle -= angle_step

        else:

            while end_angle < start_angle:
                end_angle += 2.0 * PI
            while angle < end_angle:
                path.append(
                    GPoint(position=[center[0] + radius * cos(angle), center[1] - radius * sin(angle), self.position[2]],
                           feedrate=self.feedrate, rapid=self.rapid, interpolated=True, line_number=self.line_number));
                angle += angle_step

        path.append(GPoint(position=self.position, feedrate=self.feedrate, rapid=self.rapid, line_number=self.line_number));
        return path


class GCode:
    def __init__(self, path=None):
        self.default_feedrate = None
        if path is None:
            self.path = []
        else:
            self.path = path
            self.default_feedrate = 1000

        self.rapid_feedrate = 3000
        self.initialisation = "G90G21G17G54\n"
        self.laser_mode = False
        self.steppingAxis = 2 # major cutting axis for step-down (incremental cutting). Normally z-axis on mills.


    def append_raw_coordinate(self, raw_point):
        self.path.append(GPoint(raw_point))

    def applyAxisMapping(self, axis_mapping):
        for p in self.path:
            p.axis_mapping = axis_mapping

    def applyAxisScaling(self, axis_scaling):
        for p in self.path:
            p.axis_scaling = axis_scaling


    def append(self, gpoint):
        self.path.append(gpoint)

    def combinePath(self, gcode):
        if gcode is None or gcode.path is None:
            return None
        for p in gcode.path:
            self.append(p)

    def get_draw_path(self, start = 0, end=-1, start_rotation = [0,0,0], interpolate_arcs = True):
        draw_path=[]
        current_pos = [0,0,0]
        current_rotation = None
        line=1
        for p in self.path[start:end]:
            if p.line_number==0:
                p.line_number=line
            line = max(p.line_number+1, line+1)
            try:
                point_list=[GPoint(position=p.position, feedrate=p.feedrate, rapid=p.rapid, line_number=p.line_number)]
                if interpolate_arcs:
                    point_list = p.interpolate_to_points(current_pos)
                for ip in point_list:
                    if ip.position is None:
                        ip.position = current_pos
                    if ip.rotation is not None:
                        current_rotation = ip.rotation
                    else:
                        if current_rotation is not None:
                            ip.rotation = current_rotation
                    if ip.rotation is not None: # apply rotation to path points for preview only

                        ip.position = rotate_x(ip.position, ip.rotation[0] * PI / 180.0)
                        ip.position = rotate_y(ip.position, ip.rotation[1] * PI / 180.0)
                        ip.position = rotate_z(ip.position, ip.rotation[2] * PI / 180.0)
                    draw_path.append(ip)
            except:
                traceback.print_exc()
            if (len(draw_path)>1):
                current_pos = draw_path[-1].position
        return draw_path

    def get_end_points(self, start = 0, end=-1):
        draw_path=[]
        current_pos = [0,0,0]
        for p in self.path[start:end]:
            ip=p.interpolate_to_points(current_pos)
            draw_path.append(ip[-1])
            if (len(draw_path)>1):
                current_pos = draw_path[-1].position
        return draw_path

    def getPathLength(self):
        return len(self.path)

    def appendPath(self, gcode):
        self.append(GPoint(feedrate=gcode.default_feedrate, control_point=True))
        for p in gcode.path:
            self.append(p)

    def estimate(self):
        length = 0.0
        duration = 0.0
        rapid_length = 0.0
        cut_length = 0.0
        rapid_duration = 0.0
        cut_duration = 0.0
        current_feedrate = 1000
        
        if self.default_feedrate != None:
            current_feedrate = self.default_feedrate
            
        paths = []
        paths.append(self.path)
        if len(paths) == 0 or len(paths[0]) == 0:
            return (length, duration, current_feedrate, cut_length, rapid_length, cut_duration, rapid_duration)
        lastp = None
        for segment in paths:
            for p in segment:
                if p.feedrate is not None:
                    current_feedrate = p.feedrate
                if p.feedrate is None and self.default_feedrate is not None and current_feedrate != self.default_feedrate:
                    current_feedrate = self.default_feedrate
                if p.position is not None:
                    s_length = 0
                    if lastp is not None:
                        s_length = norm(array(p.position) - lastp)
                    lastp = array(p.position)
                    if p.rapid:
                        length += s_length
                        rapid_length += s_length
                        duration += s_length / self.rapid_feedrate
                        rapid_duration += s_length / self.rapid_feedrate
                    else:
                        length += s_length
                        cut_length += s_length
                        duration += s_length / current_feedrate
                        cut_duration += s_length / current_feedrate
        # return "Path estimate: Length: %f mm;  Duration: %f minutes. Last feedrate: %f"%(length,  duration,    current_feedrate)
        return (length, duration, current_feedrate, cut_length, rapid_length, cut_duration, rapid_duration)

    def toText(self, write_header=False, pure=False):
        output = ""
        #print("laser mode:", self.laser_mode, "pure: ", pure)
        if not pure:
            estimate = self.estimate()
            if write_header:
                print("Path estimate: Length: %f mm;  Duration: %f minutes. Last feedrate: %f" % (estimate[0],
                                                                                                  estimate[1], estimate[2]))
                output += "( " + "Path estimate: Length: %f mm;  Duration: %f minutes. Last feedrate: %f" % (
                estimate[0], estimate[1], estimate[2]) + " )\n"
                output += "G90G21G17G54\n"
            if self.default_feedrate != None:
                output += "F%f\n" % (self.default_feedrate)
        complete_path = self.path
        # if self.outpaths!=None and len(self.outpaths)>0:
        #     complete_path=[]
        #     for segment in self.outpaths:
        #         complete_path+=segment
        rapid = None

        current_feedrate = self.default_feedrate
        current_gmode = "G1"
        for p in complete_path:
            if isinstance(p, GPoint):

                if p.rapid != rapid:
                    rapid = p.rapid
                    if rapid:
                        # in laser mode, issue a spindle off command before rapids
                        if self.laser_mode:
                            output += "M5\n"
                            # print "laser off"
                        output += "G0 "
                    else:
                        if self.laser_mode:
                            # in laser mode, issue a spindle on command after rapids
                            output += "M4 S1000\n"

                        if p.gmode != current_gmode:
                            current_gmode = p.gmode

                        output += current_gmode+" "
                else:
                    if p.gmode != current_gmode:
                        current_gmode = p.gmode
                        output += current_gmode+" "

            output += "" + p.to_output()
            if p.feedrate is not None and (p.control_point or p.rapid == False and p.feedrate != current_feedrate):
                current_feedrate = p.feedrate
                if not p.control_point:
                    output += "F%f" % p.feedrate
            #if p.feedrate is None and current_feedrate != self.default_feedrate:
            #    current_feedrate = self.default_feedrate
            #    output += "F%f" % current_feedrate
            output += "\n"

        if not pure:
            output += "M02\n%\n"
        return output



    def write(self, filename):
        f = open(filename, 'w')
        f.write(self.toText(write_header=True))
        f.close()
        print(filename, "saved.")


known_commands = ["G", "F", "X", "Y", "Z", "M", "I", "J", "T", "A", "B", "C"]


def is_part_of_number(s):
    return s == ' ' or s == "\t" or s == "-" or s == "+" or s == "." or (s >= "0" and s <= "9")


def parseline(line):
    p = []

    for i in range(0, len(line)):
        if line[i] == '(':
            break

        for cmd in known_commands:
            if line[i].upper().startswith(cmd):

                # find end of number
                j = i + len(cmd)
                while j < len(line) and is_part_of_number(line[j]):
                    j += 1
                value = line[i + len(cmd):j].strip()
                p.append((cmd, value))

    return p


#def write_coordinate(point, file):
#    file.write("X%fY%fZ%f\n" % (point[0], point[1], point[2]))


def write_gcode(path, filename):
    f = open(filename, 'w')
    f.write("G90G21G17G54\n")
    # go fast to starting point
    f.write("G00")
    file.write("Z%f\n" % (path[0][2]))
    write_coordinate(path[0], f)
    # linear interpolation, feedrate 800
    f.write("G01F1500")
    for p in path:
        write_coordinate(p, f)
    f.write("M02\n")


def read_gcode(filename):
    try:
        infile = open(filename)
    except:
        print("Can't open file:", filename)
        return GCode()

    datalines = infile.readlines();
    return parse_gcode(datalines)

def parse_gcode(datalines):

    x = 0
    y = 0
    z = 0
    ra = 0
    rb = 0
    rc = 0

    GCOM = ""
    feed = None
    rapid = False
    arc = False
    arcdir = None

    path = GCode()
    linecount = 0
    for l in datalines:
        i = 0
        j = 0
        k = 0
        pl = parseline(l)
        linecount += 1
        # print linecount, pl
        new_coord = False
        new_rotation = False

        try:
            for c in pl:
                if c[0].upper() == "X":
                    x = float(c[1]);
                    new_coord = True
                if c[0].upper() == "Y":
                    y = float(c[1]);
                    new_coord = True
                if c[0].upper() == "Z":
                    z = float(c[1]);
                    new_coord = True
                if c[0].upper() == "A":
                    ra = float(c[1]);
                    new_coord = True
                    new_rotation = True
                if c[0].upper() == "B":
                    rb = float(c[1]);
                    new_coord = True
                    new_rotation = True
                if c[0].upper() == "C":
                    rc = float(c[1]);
                    new_coord = True
                    new_rotation = True
                if c[0].upper() == "F":
                    feed = float(c[1])
                    if path.default_feedrate is None: # set the default feedrate to the first encountered feed
                        path.default_feedrate = feed
                if c[0].upper() == "G" and (c[1] == "0" or c[1] == "00"):
                    rapid = True
                    arc = False
                if c[0].upper() == "G" and (c[1] == "1" or c[1] == "01"):
                    rapid = False
                    arc = False
                if c[0].upper() == "G" and (c[1] == "2" or c[1] == "3" or c[1] == "02" or c[1] == "03"):  # arc interpolation
                    arc = True
                    arcdir = c[1]
                    rapid = False

                if arc and c[0].upper() == "I":
                    i = float(c[1])
                if arc and c[0].upper() == "J":
                    j = float(c[1])
        except Exception as e:
            print("conversion error in line %i:" % linecount, c)
            print(e.message)

        if new_coord:
            if arc:
                path.append(GArc(position=[x, y, z], ij= [i, j], arcdir = arcdir, feedrate=feed, rapid=rapid, command = l, line_number=linecount));
            else:
                if new_rotation:
                    path.append(GPoint(position=[x, y, z], rotation=[ra, rb, rc], feedrate=feed, rapid=rapid, command=l, line_number=linecount));
                    print("new rotation", ra, rb, rc)
                else:
                    path.append(GPoint(position=[x, y, z], feedrate=feed, rapid=rapid, command = l, line_number=linecount));

        else:
            path.append(GCommand(command =l.strip(), feedrate = feed,  line_number=linecount))
    return path
