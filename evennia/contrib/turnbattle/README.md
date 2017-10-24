# Turn based battle system framework

Contrib - Tim Ashley Jenkins 2017

This is a framework for a simple turn-based combat system, similar
to those used in D&D-style tabletop role playing games. It allows
any character to start a fight in a room, at which point initiative
is rolled and a turn order is established. Each participant in combat
has a limited time to decide their action for that turn (30 seconds by
default), and combat progresses through the turn order, looping through
the participants until the fight ends.

This folder contains multiple examples of how such a system can be
implemented and customized:

    tb_basic.py - The simplest system, which implements initiative and turn
            order, attack rolls against defense values, and damage to hit
            points. Only very basic game mechanics are included.
    
    tb_equip.py - Adds weapons and armor to the basic implementation of
            the battle system, including commands for wielding weapons and
            donning armor, and modifiers to accuracy and damage based on
            currently used equipment.
            
This system is meant as a basic framework to start from, and is modeled
after the combat systems of popular tabletop role playing games rather than
the real-time battle systems that many MMOs and some MUDs use. As such, it
may be better suited to role-playing or more story-oriented games, or games
meant to closely emulate the experience of playing a tabletop RPG.
