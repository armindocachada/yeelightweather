Python Automation — Smart Home — Using my smart lights to alert me about the weather when I wake up
===================================================================================================

<img src="/images/yeelightweatherstatic.png"/>

Waking up to warm yet rainy day with the Yeelightweather App

In this article I will show you how I improved my life, using Smart Lights, Python and a Raspberry pi. I am going to make a Smart Light from Yeelight predict the weather so I know exactly what to wear for the day ahead.

It is a pain whenever I go out of the house and I wear the wrong clothes. Sometimes I wear a coat and I should not wear one, or more often than not I forget to bring one, as the day starts deceptively warm. And those times I wish I had brought that umbrella?

Enough of complaining. Let’s resolve this once and for all with Python, a Raspberry pi and some Smart Lighting from Yeelight. And of course most important of all, we need an API that can give us an accurate forecast of the weather. Lucky for me, living in England, here we are the best in the world predicting our unpredictable weather.

My plan is to setup a raspberry Pi with a cron job that runs every morning at 7am just when I am about to wake up. It first calls the weather API to check the forecast for the day. If it finds that the weather is going to be hot, above 30 degrees, my script will set the Yeelights lights in my bedroom to deep red. If the weather going to be fair, a pale red color and for those fair days a warm white color. Or, if it is going to be cold, a cool cyan color. Finally if it is forecast to be freezing during the day, a deep blue color is shown.

Of course, being in England we can’t forget the rain, or more rarely the snow. For the rain or the snow, the light will pulse. If it is light rain or snow, the light will pulse slowly or if it is heavy, the light will pulse at a higher frequency. Brilliant, isn’t it?

Lets get started.

Since I live in London and in England, as I have just mentioned in case you forgot, we are big in predicting the weather, the Metoffice is the obvious choice for source of weather information. They have several apis. The one I went with, is the [Weather DataHub API](https://www.metoffice.gov.uk/services/data/datapoint/notifications/weather-datahub). It works, not just for England, it covers the whole world. Also it has a generous free tier of 300+ calls per day. Which is more than enough for this use case. To register and start using this API you need to go to click [HERE](https://metoffice.apiconnect.ibmcloud.com/metoffice/production/start) — Weather DataHub API Registration.

Once you have registered for an account, you need to create an application key, that allows you to use the Weather DataHub API.

The Metoffice API uses my GPS coordinates so I can get pinpoint accuracy to get the weather data.

```
def determineWeather():
    """
    We call the weather API and get the weather for the next few hours. 
    The API itself gives way too much information. All I want to know, 
    what is the minimum and maximum temperature and whether is going
    to rain or snow. And whether it is going to be light or heavy.
     >>> determineWeather()
     {'precipitation': False, 'heavyRain': False, 'heavySnow': False, 'temperatureCode': 'Hot'}
    """
    import http.client
    import json

    conn = http.client.HTTPSConnection("api-metoffice.apiconnect.ibmcloud.com")

    headers = {
        'x-ibm-client-id': "<Your-Client-ID>",
        'x-ibm-client-secret': "<Your-Client-Secret>",
        'accept': "application/json"
    }

    latitude = <MY LATITUDE>
    longitude = <MY LONGITUDE>

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
```

In the code excerpt above you can see l how I call the Metoffice [Weather DataHub API](https://www.metoffice.gov.uk/services/data/datapoint/notifications/weather-datahub). I had to register first and create an app within the Datahub in order to a client id and a client secret, which are both needed in order for the API call to work. The logic for the code above is simple. We call the weather API and get the weather for the next few hours. The API itself gives way too much information. All I want to know, what is the minimum and maximum temperature and whether is going to rain or snow. And whether it is going to be light or heavy.

Now that we have a representation of the weather, I need to setup the smart lights based on that information. Yeelight, which is the brand smart lights that I use has a convenient and simple Python library called **Yeelight**. With this API I can control my smart lights locally via internal IP address.

Below is the code I created to set my lights based on the weather information.
```
def setupWeatherFlow(bulb,weather,durationFlowSeconds=60):
    """
    We use HSV color transitions. In case there is no precipitation, the color will remain static for a minute or two.
    If there is precipitation, the light will pulse with varying levels of brightness.
    Depending on the temperature the light will be deep red if it is hot or deep blue if it is freezing.
    The flow itself will end automatically based on the durationFlowSeconds parameter.
    """
    hue = 0
    saturation = 100
    if weather['temperatureCode'] == "Hot":
        hue = 370
    elif weather['temperatureCode'] == "Warm":
        hue = 370
        saturation = 41
    elif weather['temperatureCode'] == "Fair":
        hue = 50
    elif weather['temperatureCode'] == "Cold":
        hue = 173
    elif weather['temperatureCode'] == "Freezing":
        hue = 240


    if (weather["precipitation"]):
        if weather["heavyRain"] or weather["heavySnow"]:
            duration = 100
        else:
            duration = 1000

        count = durationFlowSeconds * 1000 / duration
        transitions = [HSVTransition(hue, saturation, brightness=bright, duration=duration)
                       for bright in range(0, 100, 15)]

        flow = Flow(
            count=count,
            transitions=transitions
        )
    else:
        transitions = [HSVTransition(hue, saturation, brightness=100, duration=1000)]

        flow = Flow(
            count=durationFlowSeconds,
            transitions=transitions
        )
    bulb.turn_on()
    bulb.start_flow(flow)
```

So now we have a way to set our smart lights to change colour depending on the weather. The last bit that is missing, is that I have nowhere to run this code. I don’t want to run it on my laptop because I don’t always have it switched on. So raspberry pi comes to the rescue. Always on, so this is the ideal place to run this code from.

I like running everything inside docker as it makes easy dealing with all the dependencies, that often take a long time to install and configure.

docker-compose.yml:
```
version: "3.7"
services:
  yeelightweather:
     container_name: yeelightweather
     build:
        context: .
        dockerfile: Dockerfile
     network_mode: host
     restart: always
```
Dockerfile:
```
FROM python:rc-slim-buster
RUN TZ=Europe/London && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -y update && apt-get -y install cron
RUN pip3 install yeelight
COPY files/* /home/

#RUN chmod 755 /script.sh /entry.sh
RUN /usr/bin/crontab /home/crontab.txt

# Run the command on container startup
RUN touch /var/log/cron.log

CMD cron && tail -f /var/log/cron.log
```
I always like to use **docker compose** as it allows me to package and configure everything that I need in one place and is much more convenient than using a Dockerfile alone. The great thing about **Docker** is that it allows me to reuse **docker** images that have already been built and install new things on top of it. That is what I have done here. I used an existing image created for python which is compatible with my Macbook pro and can also run on Raspberry PI.

I installed the **yeelight** library with pip3 and also changed the default timezone in the container to be in London. Finally as I want to run my script every morning, I installed cron.

The final step is to create a .env file with all the secret keys needed. Create it inside the files/ directory using the template provided(.env\_template). You need to replace your latitude and longitude with your location coordinates so you get accurate weather. You will need to sign up for a Metoffice account in order to get a **client secret key** and **client id**.

Setup of Yeelightweather in Raspberry PI
----------------------------------------

1.  **Install docker and docker-compose**

```
$ssh pi@<your-raspberrypi>  
curl -sSL https://get.docker.com | sh\# add permission to your current user to use pi  
$sudo usermod -aG docker pi
```

You will need to reboot your raspberry pi.

After reboot, you will be installing docker-compose:

```
$sudo apt-get install -y libffi-dev libssl-dev  
$sudo apt-get install -y python3 python3-pip  
$sudo apt-get remove python-configparser  
$sudo pip3 -v install docker-compose
```

2\. **Clone the Yeelightweather project:**

```
mkdir projects  
cd projects  
git clone [https://github.com/armindocachada/yeelightweather](https://github.com/armindocachada/yeelightweather)
```

Before we attempt to initialise the Raspberry Pi, confirm that you are happy with the **Time Zone** setup in the docker container as it is shown in the **Dockerfile**:

```
FROM python:rc-slim-busterRUN **TZ=Europe/London** && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezoneRUN apt-get -y update && apt-get -y install cronRUN pip3 install yeelightCOPY files/\* /home/ #RUN chmod 755 /script.sh /entry.shRUN /usr/bin/crontab /home/crontab.txt # Run the command on container startupRUN touch /var/log/cron.log CMD cron && tail -f /var/log/cron.log
```

If you are in a different timezone, change it to your timezone. Use this wiki page as a reference guide: [https://en.wikipedia.org/wiki/List\_of\_tz\_database\_time\_zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

Next is to adjust crontab.txt inside the files directory to the time you will want to wake up. If you don’t wake up at 7:30am, then you will want to change it.

```
30 7 \* \* \* /home/start.sh >> /var/log/cron.log 2>&1# An empty line is required at the end of this file for a valid cron file.
```

Ensure that your Raspberry PI is connected to the same wifi/LAN as your Xiami Yeelight E27 Bulb. Otherwise this will not work.

```
$ cd projects/Yeelightweather  
$ docker-compose build  
$ docker-compose up -d
```

At this stage the yeelighterweather container should have started. Check that this is the case with:

```
$ docker-compose ps -aCONTAINER ID        IMAGE                             COMMAND                  CREATED             STATUS              PORTS               NAMESfa208f9ef339        yeelightweather\_yeelightweather   "/bin/sh -c 'cron &&…"   2 days ago          Up 28 hours                             yeelightweather
```

In order to test that the Xiaomi light will trigger, execute the following:

```
docker exec -it yeelightweather /home/start.sh
```

This should trigger your smart bulb and the color will be according to the temperatures forecast and if it flashes, then you know it will probably rain.

Have fun!

<img src="/images/yeelightweather_finalresult_animated.gif" />

Useful links:
=============

[Buy the Yeelight RGB WiFi Dimmable Bulb Phone App Voice Control Compatible with Alexa, Google Assistant (2-Pack) on Amazon](https://www.amazon.co.uk/Yeelight-Dimmable-Control-Compatible-Assistant/dp/B07YTMTB4Y/ref=sr_1_1_sspa?dchild=1&keywords=xiaomi+yeelight&qid=1597683157&sr=8-1-spons&psc=1&spLa=ZW5jcnlwdGVkUXVhbGlmaWVyPUFSV0UwWjhZTlZZRDMmZW5jcnlwdGVkSWQ9QTAyNzI4NDgyR0JZWTZUNEdKTFUzJmVuY3J5cHRlZEFkSWQ9QTAyNDM2NTQxNjVSUlBQQjdZSEYmd2lkZ2V0TmFtZT1zcF9hdGYmYWN0aW9uPWNsaWNrUmVkaXJlY3QmZG9Ob3RMb2dDbGljaz10cnVl)

[Yeelight Developer website](https://www.yeelight.com/en_US/developer)

[YeeLight library - python-yeelight 0.5.3 documentation](https://yeelight.readthedocs.io/en/latest/)
