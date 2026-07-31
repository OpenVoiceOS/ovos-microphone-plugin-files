## Description

OVOS Microphone Files plugin.

This plugin implements the [OVOS Plugin Manager](https://github.com/OpenVoiceOS/ovos-plugin-manager) `Microphone` interface. It reads audio from wave files instead of a real microphone. The plugin watches a folder for new files, reads each file as audio input, and deletes the file after it processes it.

Use this plugin to feed pre-recorded audio into an OVOS pipeline, for example in tests or automated demos.

## Install

```bash
pip install ovos-microphone-plugin-files
```

## Usage

The plugin watches `~/file_microphone` by default. Drop a wave file into this folder, and the plugin reads it, splits it into chunks, and queues the chunks as microphone input. After it reads a file, the plugin deletes it, unless you set `autodelete` to `False`.

Configure the plugin under `listener` in `mycroft.conf`:

```json
{
  "listener": {
    "microphone": {
      "module": "ovos-microphone-plugin-files"
    }
  }
}
```

## Related projects

- [ovos-plugin-manager](https://github.com/OpenVoiceOS/ovos-plugin-manager) — the plugin framework this microphone plugin implements.
- [ovos-listener](https://github.com/OpenVoiceOS/ovos-dinkum-listener) — the OVOS component that consumes microphone plugins.

## License

Apache-2.0
