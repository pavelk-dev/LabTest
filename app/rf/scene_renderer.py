import yaml

from app.rf.synthesizer import Synthesizer
from app.rf.waveform_registry import (
    WAVEFORM_REGISTRY
)


class RFSceneRenderer:

    @staticmethod
    def render(
            yaml_content: str
    ):
        cfg = yaml.safe_load(
            yaml_content
        )

        synth = Synthesizer(
            sample_rate=cfg[
                "sample_rate"
            ],
            N=cfg[
                "num_samples"
            ],
        )

        for component in cfg.get(
                "components",
                []
        ):
            waveform_type = (
                component["type"]
            )

            cls = (
                WAVEFORM_REGISTRY[
                    waveform_type
                ]
            )

            waveform = cls._from_dict(
                component
            )

            synth.add(waveform)

        return synth