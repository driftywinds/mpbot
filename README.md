# Marketplace Bay Bot
A vibe coded bot that uses a private API to serve information about listings on a certain marketplace

How to use: - 

## A. Already built image for private Telegram group DMs with topics enabled -

> [!WARNING]  
> My docker image builds are probably not up to date with this code, I reccommend building and using your own image as explained in part B
- copy ```compose.yml``` and ```.env``` to a docker compose enabled machine and edit .env according to your configuration (remember to supply ```ALLOWED_CHAT_ID``` and ```ALLOWED_THREAD_ID``` along with the other env variables, the bot won't function without them)
- run ```docker compose up -d```

## B. Build image and deploy bot for DMs - 

- Clone / download the repo
- change the ```Dockerfile``` according to which bot you want to use. ```GTbotfly.py``` is for <ins>**G**</ins>roups with <ins>**T**</ins>opics and ```DMflybot.py``` is for <ins>**DM**</ins>s
- run ```docker build -t mpbot .```
- edit ```compose.yml``` line to use the currently build image (change the ```image: driftywinds/mpbot:v1.0.0``` line to ```image: mpbot```)
- edit ```.env``` accordingly
- run ```docker compose up -d```
