# Feature-definition attribution

The native-window research feature names and statistical families are informed
by Daniel Groos's OpenFPL and SmartPlayFPL's Dastan. The cutoff-query/prefix-sum
implementation and pilot integration here are separate reconstruction variants;
they do not reproduce the original model binaries or all original semantics.

- [OpenFPL](https://github.com/daniegr/OpenFPL), copyright(c)2025 Daniel Groos.
- [Dastan](https://github.com/qazybekb/smartplayfpl-dastan/tree/758db9247e8b3a9a870c991064f74d8339d61cd0), copyright(c)2026 SmartPlayFPL.

The historical component reference also adapts AIrsenal's closed-form minute-scaled
Dirichlet update (https://github.com/alan-turing-institute/AIrsenal), copyright(c)2018
The Alan Turing Institute. Its team-goal and residual-points layers are separate
adaptations, not the original AIrsenal system.

The optional native-planner interface targets separately obtained
[Open FPL Solver](https://github.com/solioanalytics/open-fpl-solver/tree/ec65f5e2b2be34441cb4b2a9efafea1ec0fe3b79).
Its source and binaries are not bundled. Its [own license](https://github.com/solioanalytics/open-fpl-solver/blob/ec65f5e2b2be34441cb4b2a9efafea1ec0fe3b79/LICENSE)
applies independently; this repository's MIT license does not relicense it or
the separately installed optional packages. The adapter's source hashes and
explicit rule/financial compatibility changes distinguish it from the untouched
external manager. No original-system performance equivalence is implied.

The OpenFPL, Dastan and AIrsenal works listed above use the MIT License.
The notice below is retained for their feature
definitions. Source-code licensing does not grant rights to redistribute
third-party FPL/Understat/raw snapshot datasets; no such datasets are included.

MIT License

Copyright (c) 2025 Daniel Groos
Copyright (c) 2026 SmartPlayFPL
Copyright (c) 2018 The Alan Turing Institute

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
