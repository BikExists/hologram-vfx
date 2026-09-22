# Third-Party Software Notices and Disclosures

This document lists the third-party software libraries, tools, and pre-trained machine learning models incorporated into, bundled with, or utilized by **Holographic VFX**, along with their respective open-source license terms and attributions.

Holographic VFX is grateful to the authors and maintainers of these open-source projects.

---

## 1. Runtime Dependencies

The following third-party components are utilized at runtime for computer vision, machine learning inference, and numerical processing:

| Component | Verified Version / Range | Purpose | License | Upstream Project URL |
| :--- | :--- | :--- | :--- | :--- |
| **OpenCV (`opencv-python`)** | `5.0.0.93` (`>=4.8.0`) | Video capture handling, image transformation, drawing primitives, HighGUI presentation | **Apache License 2.0** | [https://github.com/opencv/opencv-python](https://github.com/opencv/opencv-python) |
| **Google MediaPipe (`mediapipe`)** | `0.10.14` (`>=0.10.14,<0.11.0`) | Real-time 21-joint 3D hand tracking and palm detection pipeline | **Apache License 2.0** | [https://github.com/google/mediapipe](https://github.com/google/mediapipe) |
| **NumPy (`numpy`)** | `2.4.6` (`>=1.24.0`) | Fast array manipulation, spatial coordinate transforms, procedural mesh matrices | **BSD 3-Clause License** | [https://numpy.org](https://numpy.org) |
| **Protocol Buffers (`protobuf`)** | `4.25.9` | Data serialization format used by MediaPipe calculator graphs and landmarks | **BSD 3-Clause License** | [https://github.com/protocolbuffers/protobuf](https://github.com/protocolbuffers/protobuf) |
| **FlatBuffers (`flatbuffers`)** | `25.12.19` | Cross-platform serialization format used by TensorFlow Lite models | **Apache License 2.0** | [https://github.com/google/flatbuffers](https://github.com/google/flatbuffers) |
| **Abseil Python (`absl-py`)** | `2.5.0` | Common Python utility library used by Google MediaPipe | **Apache License 2.0** | [https://github.com/abseil/abseil-py](https://github.com/abseil/abseil-py) |
| **Attrs (`attrs`)** | `26.1.0` | Classes and data attribute handling used by MediaPipe | **MIT License** | [https://www.attrs.org](https://www.attrs.org) |
| **CFFI (`cffi`)** | `2.1.1` | Foreign Function Interface for Python to call C code | **MIT License** | [https://cffi.readthedocs.io](https://cffi.readthedocs.io) |
| **Pillow (`pillow`)** | `12.3.0` | Python Imaging Library utilized by MediaPipe visualization tools | **HPND License** | [https://python-pillow.org](https://python-pillow.org) |
| **Python Runtime** | `3.11.16` | Underlying programming language runtime | **PSF License Agreement** | [https://www.python.org](https://www.python.org) |

---

## 2. Build & Packaging Tooling

The following components are used to compile the standalone executable and Windows installer:

| Component | Verified Version / Range | Purpose | License | Upstream Project URL |
| :--- | :--- | :--- | :--- | :--- |
| **PyInstaller (`pyinstaller`)** | `6.22.3` (`>=6.0.0`) | Standalone application bundler creating `--onedir` distribution | **GPLv2 with PyInstaller Exception** | [https://pyinstaller.org](https://pyinstaller.org) |
| **Inno Setup** | `6.x` | Windows installer compiler producing `HolographicVFX-Setup.exe` | **Inno Setup License (Modified BSD)** | [https://jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php) |

> **Note on PyInstaller Licensing**: PyInstaller is licensed under GPLv2 with a special exception that explicitly permits users to bundle and distribute programs without subjecting the bundled program to the GPLv2 license.

---

## 3. Development & Testing Dependencies

The following tools are used during development and automated regression testing:

| Component | Verified Version / Range | Purpose | License | Upstream Project URL |
| :--- | :--- | :--- | :--- | :--- |
| **pytest (`pytest`)** | `9.1.1` (`>=7.0.0`) | Automated test runner and assertion framework | **MIT License** | [https://pytest.org](https://pytest.org) |
| **Pluggy (`pluggy`)** | `1.6.0` | Plugin management framework used by pytest | **MIT License** | [https://github.com/pytest-dev/pluggy](https://github.com/pytest-dev/pluggy) |

---

## 4. Pre-Trained Machine Learning Models Disclosure

The standalone package bundles pre-trained binary machine learning models extracted from the `mediapipe` package:

* **Bundled Model Assets**:
  * `hand_landmark_tracking_cpu.binarypb`
  * `palm_detection_full.tflite`
  * `palm_detection_lite.tflite`
* **Origin**: Developed and published by Google LLC as part of the MediaPipe project.
* **License**: Distributed under the **Apache License, Version 2.0**.
* **Ownership**: Holographic VFX does not claim ownership of these pre-trained model weights, topologies, or training pipelines. They are redistributed under the terms of the Apache License 2.0.

---

## 5. Project-Created Assets Disclosure

* **Application Icons & Artwork**:
  * `assets/icon.ico`, `assets/icon.png`: Application and executable icons created for Holographic VFX.
  * `assets/logo.png`: Project banner logo created for Holographic VFX.
* **Procedural VFX & Hologram Geometry**:
  * Procedural wireframe meshes and mathematical models (Energy Orb, Cyber Cube, Holographic Planet, Ghost Orchid, Bhondu Face, and Bioluminescent Jellyfish) implemented in `src/objects/` and `src/vfx/` are custom Python code created for this repository.

---

## 6. Common Third-Party License Texts & Notices

### Apache License, Version 2.0
*(Applies to OpenCV, MediaPipe, FlatBuffers, Abseil Python, and MediaPipe model assets)*

```text
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### BSD 3-Clause License
*(Applies to NumPy and Protocol Buffers)*

```text
Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### MIT License
*(Applies to pytest, Pluggy, Attrs, and CFFI)*

```text
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Inno Setup License
*(Applies to Inno Setup installer compilation)*

```text
Inno Setup is Copyright (C) 1997-2024 Jordan Russell. Portions by Martijn Laan.
Inno Setup is free software; you can redistribute it and/or modify it under
the terms of the Inno Setup license:
https://jrsoftware.org/files/is/license.txt
```
