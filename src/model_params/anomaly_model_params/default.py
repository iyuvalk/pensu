# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

MODEL_PARAMS = {
  "model": "HTMPrediction",
  "version": 1,
  "predictAheadTime": None,
  "modelParams": {
    "sensorParams": {
      "verbosity": 0,
      "encoders": {
        "timestamp_timeOfDay": {
          "fieldname": "timestamp",
          "timeOfDay": [
            21,
            1
          ],
          "type": "DateEncoder",
          "name": "timestamp_timeOfDay"
        },
        "value": {
          "fieldname": "value",
          "seed": 1,
          "resolution": 0.88,
          "name": "value",
          "type": "RandomDistributedScalarEncoder"
        },
        "timestamp_weekend": {
          "fieldname": "timestamp",
          "type": "DateEncoder",
          "name": "timestamp_weekend",
          "weekend": 21
        }
      },
      "sensorAutoReset": None
    },
    "spParams": {
      "columnCount": 2048,
      "spVerbosity": 0,
      "localAreaDensity": -1.0,
      "spatialImp": "cpp",
      "inputWidth": 946,
      "synPermInactiveDec": 0.005,
      "synPermConnected": 0.1,
      "synPermActiveInc": 0.04,
      "seed": 1956,
      "numActiveColumnsPerInhArea": 40,
      "boostStrength": 3.0,
      "globalInhibition": 1,
      "potentialPct": 0.85
    },
    "trainSPNetOnlyIfRequested": False,
    "clParams": {
      "steps": "1,5",
      "maxCategoryCount": 1000,
      "implementation": "cpp",
      "alpha": 0.1,
      "verbosity": 0,
      "regionName": "SDRClassifierRegion"
    },
    "tmParams": {
      "columnCount": 2048,
      "pamLength": 1,
      "permanenceInc": 0.1,
      "outputType": "normal",
      "initialPerm": 0.21,
      "seed": 1960,
      "maxSegmentsPerCell": 128,
      "temporalImp": "cpp",
      "activationThreshold": 16,
      "cellsPerColumn": 32,
      "permanenceDec": 0.1,
      "minThreshold": 12,
      "verbosity": 0,
      "maxSynapsesPerSegment": 32,
      "globalDecay": 0.0,
      "newSynapseCount": 20,
      "maxAge": 0,
      "inputWidth": 2048
    },
    "tmEnable": True,
    "spEnable": True,
    "inferenceType": "TemporalAnomaly"
  }
}
