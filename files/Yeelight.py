# minimum percentage at which point we consider it is quite likely
# to rain

probabilityOfPrecipitationThreshold= 50
probabilityOfHeavyRainThreshold = 50
ProbabilityOfHeavySnowThreshold = 50


# weather is freezing if minTemperature is below 0
# weather is cold if minTemperature > 0 and below 10
# weather is fair if minTemperature > 10 and below 20
# weather is warm if maxTemperature > 20 and below 25
# weather is hot if maxTemperature >= 25
def classifyTemperature(minTemperature, maxTemperature):
    if minTemperature <= 0:
        return "Freezing"
    elif minTemperature < 10:
        return "Cold"
    # to define anything more than cold, we look at the maximum temperature within the day
    elif maxTemperature >= 10 and maxTemperature < 20:
        return "Fair"
    elif maxTemperature >= 20 and maxTemperature < 25:
        return "Warm"
    elif maxTemperature >= 25:
        return "Hot"



def determineWeather():
    import http.client
    import json

    conn = http.client.HTTPSConnection("api-metoffice.apiconnect.ibmcloud.com")

    headers = {
        'x-ibm-client-id': "24858361-ac19-438c-9962-862572052efa",
        'x-ibm-client-secret': "rC6mH0oT7sU2dJ3qA7sG1bG3fK4wK0vH8rL4vR5rA7dH1gC3lQ",
        'accept': "application/json"
    }

    latitude = 51.485741
    longitude = 0.027864

    conn.request("GET",
                 "/metoffice/production/v0/forecasts/point/daily?excludeParameterMetadata=false&includeLocationName=true&latitude={}&longitude={}".format(
                     latitude, longitude), headers=headers)

    res = conn.getresponse()
    data = res.read()

    weather = json.loads(data.decode("utf-8"))

    precipitation = False
    heavyRain = False
    heavySnow = False
    minTemperature = None
    maxTemperature = None
    for timeForecast in weather['features'][0]['properties']['timeSeries']:
        probabilityOfPrecipitation = timeForecast['dayProbabilityOfPrecipitation']
        dayProbabilityOfHeavyRain = timeForecast['dayProbabilityOfHeavyRain']
        dayProbabilityOfHeavySnow = timeForecast['dayProbabilityOfHeavySnow']
        if probabilityOfPrecipitation >= probabilityOfPrecipitationThreshold:
            precipitation = True
        if dayProbabilityOfHeavyRain >= probabilityOfHeavyRainThreshold:
            heavyRain = True
        if dayProbabilityOfHeavySnow >= ProbabilityOfHeavySnowThreshold:
            heavySnow = True

        temperature = timeForecast['dayMaxFeelsLikeTemp']

        if (not minTemperature or temperature < minTemperature ):
            minTemperature = temperature

        if (not maxTemperature or temperature > maxTemperature ):
            maxTemperature = temperature



    temperatureCode = classifyTemperature(minTemperature, maxTemperature)

    return {"precipitation": precipitation, "heavyRain": heavyRain, "heavySnow": heavySnow, "temperatureCode": temperatureCode }


def setupWeatherFlow(bulbIp,weather,durationFlowSeconds=60):
  try: 
    bulb = Bulb(bulbIp)
    hue = 0
    saturation = 100
    if weather['temperatureCode'] == "Hot":
        hue = 370
        (red,green,blue) = (255, 0, 0)
    elif weather['temperatureCode'] == "Warm":
        hue = 370
        saturation = 41
        (red,green,blue)=(250,150,152)
    elif weather['temperatureCode'] == "Fair":
        hue = 50
        (red,green,blue) = (255, 213, 0)
    elif weather['temperatureCode'] == "Cold":
        hue = 66, 
        (red,green,blue) = (50, 168, 164)
    elif weather['temperatureCode'] == "Freezing":
        hue = 240
        (red,green,blue) = (0,0,255)
    if (weather["precipitation"]):
        if weather["heavyRain"] or weather["heavySnow"]:
            duration = 200
        else:
            duration = 2000 

        count = (durationFlowSeconds * 1000) / duration
        transitions = yeelight.transitions.pulse(red, green, blue, duration, 100) 
        flow = Flow(
            count=count,
            action=Action.recover,
            transitions=transitions
        )
        print("There is rain/snow. heavyRain={}, heavySnow={}".format(weather["heavyRain"],weather["heavySnow"]))
    else:
        transitions = [HSVTransition(hue, saturation, brightness=100, duration=1000)]

        flow = Flow(
            count=durationFlowSeconds,
            transitions=transitions
        )

        print("There is no precipitation. Setting just the color of the temperature ahead")
    bulb.turn_on()
    bulb.start_flow(flow)
  except:
   print("Error setting flow in bulb",file=sys.stderr)  
   print("Unexpected error:", sys.exc_info()[0])
   pass
   
from multiprocessing import Process
if __name__ == '__main__':
    print("main line")

    weather = determineWeather()
    import yeelight.transitions
    from yeelight import *
    from yeelight import discover_bulbs,Bulb
    from yeelight import HSVTransition,Flow,transitions
    from yeelight.flow import Action
    import sys
    bulbs = discover_bulbs()
    for b in bulbs:
       print("starting {}".format(b['ip']))
       bulbIp = b['ip']
       p = Process(target=setupWeatherFlow, args=(bulbIp,weather))
       p.start()
       p.join()

