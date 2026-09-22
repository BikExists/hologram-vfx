# Holographic VFX Terms of Use & Disclaimer

This document outlines the operational expectations, pre-release development status, and disclaimers for **Holographic VFX**.

This document is an informational project disclaimer intended to set clear expectations for users and developers. It is not attorney-reviewed legal counsel.

---

## 1. Pre-Release Software Notice

Holographic VFX is an experimental, pre-release software project (`v0.x.x-dev`). It is actively evolving, and features, interfaces, keyboard shortcuts, and performance behaviors are subject to change between milestones. It is provided primarily for evaluation, testing, and development experimentation.

---

## 2. Software Provided "As-Is"

The software is provided "AS IS", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the authors, maintainers, or contributors be held liable for any claim, damages, or other liability arising from the use of, or inability to use, this software.

---

## 3. User Hardware & Permissions

To operate, Holographic VFX requires access to a video capture device (webcam).

* **User Responsibility**: The user is responsible for ensuring their operating system grants the necessary camera permissions to the application (via Windows Settings or macOS Security & Privacy).
* **Hardware Suitability**: The user is responsible for verifying that their hardware (CPU, RAM, camera) meets the operational requirements described in [SYSTEM_REQUIREMENTS.md](SYSTEM_REQUIREMENTS.md).
* **Adequate Lighting**: The user acknowledges that tracking fidelity depends fundamentally on real-world ambient room lighting and camera sensor auto-exposure.

---

## 4. Operational Availability & Tracking Limits

* **No Guarantee of Uninterrupted Operation**: There is no guarantee that hand tracking will remain locked under all conditions, lighting environments, or rapid hand movements.
* **Camera Sensor Variations**: Visual frame rates are tied to the physical capabilities and exposure settings of the user's camera hardware.
* **Grace Period & Recovery**: The software includes internal error containment and a 4-frame tracking grace period, but temporary tracking loss or edge-of-frame dropouts are normal operational occurrences in vision-based systems.

---

## 5. Third-Party Components & Dependencies

Holographic VFX incorporates and links against multiple open-source libraries and pre-trained machine learning models (including OpenCV, Google MediaPipe, and NumPy). Each third-party component is governed by its own respective license terms, as documented in [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md).

---

## 6. Project License Status & Maintainer Authority

* **No Explicit Project License Yet**: As of the current repository state, an explicit project-wide open-source license (such as MIT or Apache 2.0) has not yet been formally committed.
* **Human Decision Required**: Formal selection and adoption of a project license is an administrative decision reserved for the repository owner and maintainer (`BikExists`).
* **Third-Party Rights**: Nothing in this document or the project modifies, overrides, or limits the open-source rights granted by third-party upstream components under their respective licenses.

---

## 7. Informational Purpose

This disclaimer serves to document the current technical realities and development expectations of Holographic VFX. If you require legal advice regarding software distribution, intellectual property, or compliance, please consult qualified legal counsel.
