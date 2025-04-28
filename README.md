# Laser-Tag
A Raspberry Pi Pico W infraRed game written in MicroPython

Hello dear users! I am sagi, a high-schooler who is supposed to send in my project in one month!
I wanted to make a socket programming project, but something more "niche"

The project works like that:

There is a server side computer, which handles basically everything in the game.
On the other side of the communication, there are two types of clients:
1. Player - A pico pi user with a "laser kit" including a IR gun and a IR vest, which are basically a receiver and a sender of IR signals!
2. Configurator - The "boss" of each playing room. He decides the length of the game, he can freeze the game, etc. He can(optionally) seperate the game into teams.

I will need to solder all parts together, but currently I am just beginning.

I am using 330 ohm resistors for the IR receivers
