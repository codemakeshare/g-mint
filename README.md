# g-mint
CAM Software and GRBL GUI (WIP, experimental)
============================================

This is a very basic, generic graphical frontend with a collection of CAM algorithms. Very early version.

EXPERIMENTAL SOFTWARE! Use at your own risk. Carefully check and verify any GCode before running on actual machines!
--------------------------------------------------------------------------------------------------------------------

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Hopefully you will find it interesting. It can do a number of CAM operations for 2.5D and 3D surfacing, thread milling and boring, as well as lathe toolpaths. However, for now, there is no documentation yet, the user interface is not very intuitive, and there may be bugs. Carefully check any GCode, and simulate it, before running it on a machine. Bad GCode may damage machines, and cause injuries or harm. Use on your own risk. 

At the moment, it will probably be most interesting to programmers who want to dive into CAM algorithms and might find it interesting. I've used it for actual machining, but the lack of documentation or a user-friendly GUI will make that challenging for others.

What can it do?
---------------

There are 3 main programs: mincam.py, mint.py and lint.py

mincam.py
---------

- load STL files (ASCII format only!)
- generate toolpaths:
   - tool widget
      - tool definitions for slot and ball mills, with precise depth calculation based on triangles, or simple based on height map (deprecated)
      - definition of prismatic lathe tools
   - 2.5D machining:
      - slice at defined height to create 2D outline, and contour offsetting
      - medial line algorithm (can be used for trochoidal milling in path tools)
   - 3D machining (generate a pattern, and drop tool to 3D surface)
   - generators for thread milling and boring
   - lathe operations: plunging, following inside and outside, with prismatic tools (optional corner radius)
- path operations
   - multiple depth stepping with ramp-down
   - clean paths (remove redundant points on a straight line)
   - smooth paths (replace line segments with arcs within a tolerance)
   - trochoidal interpolation along paths (makes most sense with medial line paths)
- GRBL machine interface
   - real-time jogging
   - DRO with direct data entry
   - GCode editor for ad-hoc manual programming and machining
   - run currently active GCode from the path tool

mint.py
-------
Just the GRBL machine interface, for mills

lint.py
-------
GRBL machine interface for lathes. Can be run on raspberry pi with the official touch screen.


Setup:
-------
Developed and tested on Ubuntu. 

dependencies (may be incomplete):
- python3
- PyQT5
- pyqtgraph
- pyclipper
- pyserial

on ubuntu:
sudo apt install python3 python3-pyqt5 python3-pyqt5.qtopengl python3-pyqt5.qsci python3-opengl python3-numpy python3-scipy python3-pip python3-svg.path python3-shapely python3-serial python3-freetype

pip3 install pyqtgraph
pip3 install pyclipper
pip3 install svgpathtools

to run:
python3 mincam.py

python3 mint.py

python3 lint.py [-f]

  -f fullscreen



