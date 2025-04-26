# Piplayer
A modular headless lightweight player for SBCs (Raspberry etc) with low cpu power in mind


## Install

It is not recommended to use conda as environment

Run
```
sudo bash install.sh
```

## Compatible Formats

### Audio

- wav (recommended)
- mp3

### Sequences

- mid (with multiple tracks)


## How to use

If using midi files to control sequences, first run:

```
python piplayer_setup.py myfile.mid
```

And for playback run:

```
python piplayer beat.wav --sequence seq.mid --loop --gui
```

