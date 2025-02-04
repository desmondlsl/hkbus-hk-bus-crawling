import json
from sys import stderr
from haversine import haversine, Unit

routeList = []
stopList = {}
stopMap = {}

def getRouteObj ( route, co, stops, bound, orig, dest, seq, fares, faresHoliday, freq, jt, nlbId, gtfsId, serviceType = 1):
  return {
    'route': route,
    'co': co,
    'stops': stops,
    'serviceType': serviceType,
    'bound': bound,
    'orig': orig,
    'dest': dest,
    'fares': fares,
    'faresHoliday': faresHoliday,
    'freq': freq,
    'jt': jt,
    'nlbId': nlbId,
    'gtfsId': gtfsId,
    'seq': seq
  }

def isGtfsMatch(knownRoute, newRoute):
  if knownRoute['gtfsId'] is None: return True
  if 'gtfs' not in newRoute: return True 

  return knownRoute['gtfsId'] in newRoute['gtfs']
  
def importRouteListJson( co ):
  _routeList = json.load(open('routeFareList.%s.cleansed.json'%co, 'r', encoding='UTF-8'))
  _stopList = json.load(open('stopList.%s.json'%co, 'r', encoding='UTF-8'))
  for stopId, stop in _stopList.items():
    if stopId not in stopList:
      try:
        stopList[stopId] = {
          'name': {
            'en': stop['name_en'],
            'zh': stop['name_tc']
          },
          'location': {
            'lat': float(stop['lat']),
            'lng': float(stop['long'])
          }
        }
      except:
        print("Problematic stop: ", stopId, file=stderr)
  
  for _route in _routeList:
    found = False
    speicalType = 1
    orig = {'en': _route['orig_en'].replace('/', '／'), 'zh': _route['orig_tc'].replace('/', '／')}
    dest = {'en': _route['dest_en'].replace('/', '／'), 'zh': _route['dest_tc'].replace('/', '／')}
    
    for route in routeList:
      if _route['route'] == route['route'] and co in route['co'] and isGtfsMatch(route, _route):
        # skip checking if the bound is not the same
        if co in route["bound"] and route['bound'][co] != _route['bound']:
          continue
        
        if len(_route['stops']) == route['seq']:
          dist = 0
          merge = True
          for stop_a, stop_b in zip( _route['stops'], route['stops'][0][1] ):
            stop_a = stopList[stop_a]
            stop_b = stopList[stop_b]
            dist = haversine( 
              (stop_a['location']['lat'], stop_a['location']['lng']), 
              (stop_b['location']['lat'], stop_b['location']['lng']),
              unit=Unit.METERS # specify that we want distance in metres, default unit is km
            )
            merge = merge and dist < 300
          if merge:
            found = True
            route['stops'].append((co, _route['stops']))
            route['bound'][co] = _route['bound']
        elif _route['orig_en'].upper() == route['orig']['en'].upper() and _route['dest_en'].upper() == route['dest']['en'].upper():
          speicalType = int(route['serviceType']) + 1
          if _route["route"] == '606' and _route['dest_tc'].startswith("彩雲"):
            print("Yes", speicalType)
    
    if not found:
      routeList.append( 
        getRouteObj(
          route = _route['route'], 
          co = _route['co'], 
          serviceType = _route.get('service_type', speicalType), 
          stops = [(co, _route['stops'])],
          bound = {co: _route['bound']},
          orig = orig,
          dest = dest,
          fares = _route.get('fares', None),
          faresHoliday = _route.get('faresHoliday', None),
          freq = _route.get('freq', None),
          jt = _route.get('jt', None),
          nlbId = _route.get('id', None),
          gtfsId = _route.get('gtfsId', _route.get('gtfs', [None])[0]),
          seq = len(_route['stops'])
        )
      )

def isMatchStops(stops_a, stops_b, debug = False):
  if len(stops_a) != len(stops_b):
    return False
  for v in stops_a:
    if stopMap.get(v, [[None,None]])[0][1] in stops_b:
      return True
  return False

def getRouteId(v):
  return '%s+%s+%s+%s'%(v['route'], v['serviceType'], v['orig']['en'], v['dest']['en'])

def smartUnique():
  _routeList = []
  for i in range(len(routeList)):
    if routeList[i].get('skip', False):
      continue
    founds = []
    # compare route one-by-one
    for j in range(i+1, len(routeList)):
      if routeList[i]['route'] == routeList[j]['route'] \
        and len(routeList[i]['stops']) == len(routeList[j]['stops']) \
        and len([co for co in routeList[i]['co'] if co in routeList[j]['co']]) == 0 \
        and isMatchStops(routeList[i]['stops'][0][1], routeList[j]['stops'][0][1]):
        founds.append( j )
      elif routeList[i]['route'] == routeList[j]['route'] \
        and str(routeList[i]['serviceType']) == str(routeList[j]['serviceType']) \
        and routeList[i]['orig']['en'] == routeList[j]['orig']['en'] \
        and routeList[i]['dest']['en'] == routeList[j]['dest']['en']:
        routeList[j]['serviceType'] = str(int(routeList[j]['serviceType'])+1)

    # update obj
    for found in founds:
      routeList[i]['co'].extend(routeList[found]['co'])
      routeList[i]['stops'].extend( routeList[found]['stops'] )
      routeList[found]['skip'] = True

    # append return array
    _routeList.append(routeList[i])

  return _routeList
      
importRouteListJson('kmb')
importRouteListJson('ctb')
importRouteListJson('nlb')
importRouteListJson('lrtfeeder')
importRouteListJson('gmb')
importRouteListJson('lightRail')
importRouteListJson('mtr')
importRouteListJson('sunferry')
importRouteListJson('fortuneferry')
importRouteListJson('hkkf')
routeList = smartUnique()
for route in routeList:
  route['stops'] = {co: stops for co, stops in route['stops']}

holidays = json.load(open('holiday.json', 'r', encoding='UTF-8'))
serviceDayMap = json.load(open('gtfs.json', 'r', encoding='UTF-8'))['serviceDayMap']

def standardizeDict(d):
  return {key: value if not isinstance(value, dict) else standardizeDict(value) for key, value in sorted(d.items())}

db = standardizeDict({
  'routeList': {getRouteId(v): v for v in routeList},
  'stopList': stopList,
  'stopMap': stopMap,
  'holidays': holidays,
  'serviceDayMap': serviceDayMap,
})

with open( 'routeFareList.mergeRoutes.json', 'w', encoding='UTF-8' ) as f:
  f.write(json.dumps(db, ensure_ascii=False, indent=4))

with open( 'routeFareList.mergeRoutes.min.json', 'w', encoding='UTF-8' ) as f:
  f.write(json.dumps(db, ensure_ascii=False, separators=(',', ':')))
