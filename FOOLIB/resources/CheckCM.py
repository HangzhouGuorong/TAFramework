# # @package CMtools
#  Tools for CM testing.
#  \file CheckCM.py

import getopt, sys, os

# SAX
from xml.sax import make_parser
from xml.sax.handler import feature_namespaces
from xml.sax._exceptions import SAXParseException

from Definitions import *
import PDDBData, Compare


# # Usage instructions.
def usage(program):
  head, tail = os.path.split(program)
  program = tail
  print "Usage:"
  print program, "-p <PDDB report> -f <final UL plan> [-d <DL plan> -i <initial UL plan> -e <CM events> -r <plan feedbacks>]"
  print ""
  print "-p <PDDB report>     PDDB metadata of RNC SW under test"
  print "-f <final UL plan>   RNW upload plan after the test"
  print "-d <DL plan>         RNW download plan"
  print "-i <initial UL plan> RNW upload plan before the test"
  print "-e <CM events>       text file of CM events received by NetActStub"
  print "-r <plan feedbacks>  text file of plan feedbacks received by NetActStub"
  print ""
  print "Examples:"
  print ""
  print "analyze final upload plan only: no extra/missing/illegal parameters:"
  print '>', program, "-p PDDB_REP.XML -f RNWPLANU.XML"
  print ""
  print "analyze download and final upload plan: download plan changes are done:"
  print '>', program, "-p PDDB_REP.XML -d RNWPLAND.XML -f RNWPLANU.XML"
  print ""
  print "analyze initial upload plan, final upload plan, download plan and CM events:"
  print '>', program, "-p PDDB_REP.XML -i RNWPLANU1.XML -d RNWPLAND.XML -f RNWPLANU2.XML -e netactstub-20110401-091842-notif.log"
  sys.exit(1)


# # Analyze CM testing results.
def main():

  try:
    opts, args = getopt.getopt(sys.argv[1:], 'p:f:d:i:e:r:')
  except getopt.GetoptError:
    usage(sys.argv[0])
  if len(opts) < 2:
    usage(sys.argv[0])
  pddbReport = None
  finalUploadPlan = None
  initialUploadPlan = None
  dlPlan = None
  cmEvents = None
  planFeedbacks = None
  for opt in opts:
    o, v = opt
    if o == '-p':
      if v == '':
        usage(sys.argv[0])
      pddbReport = v
      if os.path.exists(pddbReport) == False:
        print "File not found:", pddbReport
        sys.exit(1)
    elif o == '-f':
      if v == '':
        usage(sys.argv[0])
      finalUploadPlan = v
    elif o == '-d':
      if v == '':
        usage(sys.argv[0])
      dlPlan = v
    elif o == '-i':
      if v == '':
        usage(sys.argv[0])
      initialUploadPlan = v
    elif o == '-e':
      if v == '':
        usage(sys.argv[0])
      cmEvents = v
    elif o == '-r':
      if v == '':
        usage(sys.argv[0])
      planFeedbacks = v
    else:
      usage(sys.argv[0])

  # these are mandatory
  if pddbReport == None:
    usage(sys.argv[0])
  if finalUploadPlan == None:
    usage(sys.argv[0])
  if initialUploadPlan != None and dlPlan == None:
    usage(sys.argv[0])
 
  pddbData = PDDBData.PDDBData()
  parser = make_parser()
  parser.setFeature(feature_namespaces, 0)
  parser.setContentHandler(pddbData)
  try:
    parser.parse(pddbReport)
  except ValueError:
    print ERROR_MSG
    print "Can't read file:", pddbReport
    sys.exit(3)
  except SAXParseException:
    print ERROR_MSG
    print "XML parsing error:", pddbReport
    sys.exit(4)

  pddbData.__paramNameDictionary = {}  # dictionary to store parameter names of every managed object
  pddbData.__paramDataDictionary = {}  # dictionary to store parameter data of every parameter
  pddbData.__childObjectDictionary = {}  # dictionary containing list of children of every managed objects (if any)
  pddbData.__managedObjectList = []  # list of all RNW objects
  pddbData.__currentObject = None  # current object SAX is processing (e.g. WBTS)
  pddbData.__currentChildObjectList = []  # list of child objects of current object
  pddbData.__currentParamLevel = -1  # 'deepness' of structure, there may be several parameters inside of one
  pddbData.__currentChildDictionary = {}  # dictionary of child parameters in all levels
  pddbData.__currentParamStackList = []  # upper level parameters of struct
    
  """  
  compare = Compare.Compare(pddbData, initialUploadPlan, finalUploadPlan, dlPlan, cmEvents, planFeedbacks)
  if dlPlan != None:
    compare.analyzeDownload()
  compare.analyzeUploadAndEvsnts()
  print "\n%d problems found" % compare.getProblemCount()
  """

if __name__ == '__main__':
  main()
  sys.exit(0)
