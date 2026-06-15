from app.rf.rf_blocks import (
    RFAmplifier,
    BandpassFilter,
    Mixer,
)

RF_BLOCK_REGISTRY = {
    "RFAmplifier": RFAmplifier,
    "BandpassFilter": BandpassFilter,
    "Mixer": Mixer,
}