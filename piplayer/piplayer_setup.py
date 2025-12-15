# piplayer_setup.py
import json
import argparse
from piplayer.modules.sequence_loader import SequenceLoader

PROTOCOL_CHOICES = {
    0: "NONE",
    1: "GPIO",
    2: "DMX",
    3: "HTTP_SWITCH",
}

def setup_configuration(midi_file: str, output_file: str) -> None:
    print(f"Loading MIDI file: {midi_file}")
    sequence = SequenceLoader(midi_file)

    if not sequence.track_names:
        print("No tracks found in the MIDI file!")
        return

    config = {
        "tracks": {}
    }

    print("\nTracks found:")
    for idx, track in enumerate(sequence.track_names):
        name = track if track.strip() else "--empty--"
        print(f"[{idx}] {name}")

    print("\nAssign output protocol per track:")

    for track in sequence.track_names:
        track_name = track if track.strip() else "--empty--"

        print(f"\nTrack: {track_name}")
        for num, proto in PROTOCOL_CHOICES.items():
            print(f"[{num}] {proto}")

        while True:
            try:
                choice = int(input("Select protocol number: ").strip())
                if choice not in PROTOCOL_CHOICES:
                    print("Invalid choice.")
                    continue

                proto = PROTOCOL_CHOICES[choice]
                entry = {"protocol": proto}

                if proto == "HTTP_SWITCH":
                    ip = input("IP address for this track: ").strip()
                    electric_group = int(input("Electric group: ").strip())

                    entry["ip"] = ip
                    entry["electric_group"] = electric_group

                config["tracks"][track_name] = entry
                break

            except ValueError:
                print("Invalid input, try again.")

    with open(output_file, "w") as f:
        json.dump(config, f, indent=4)

    print(f"\n✅ Configuration saved to {output_file}")
    print(f"Use it with: piplayer ... -c {output_file}")

def main():
    parser = argparse.ArgumentParser(description="PiPlayer Setup Tool")
    parser.add_argument("midi_file", help="Path to the MIDI (.mid) file")
    parser.add_argument("-o", "--output", default="config.json",
                        help="Output config file")
    args = parser.parse_args()

    setup_configuration(args.midi_file, args.output)

if __name__ == "__main__":
    main()
