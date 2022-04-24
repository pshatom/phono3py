"""Kubo thermal conductivity base class."""
# Copyright (C) 2022 Atsushi Togo
# All rights reserved.
#
# This file is part of phono3py.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# * Neither the name of the phonopy project nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import numpy as np
from phonopy.units import Kb, THzToEv

from phono3py.phonon.group_velocity_matrix import GroupVelocityMatrix
from phono3py.phonon.heat_capacity_matrix import mode_cv_matrix


class ConductivityKuboMixIn:
    """Thermal conductivity mix-in for group velocity matrix."""

    @property
    def kappa(self):
        """Return kappa."""
        return self._kappa

    @property
    def mode_kappa_mat(self):
        """Return mode_kappa_mat."""
        return self._mode_kappa_mat

    def _init_velocity(self, gv_delta_q):
        self._velocity_obj = GroupVelocityMatrix(
            self._pp.dynamical_matrix,
            q_length=gv_delta_q,
            symmetry=self._pp.primitive_symmetry,
            frequency_factor_to_THz=self._pp.frequency_factor_to_THz,
        )

    def _set_cv(self, i_gp, i_data):
        """Set heat capacity matrix.

        x=freq/T has to be small enough to avoid overflow of exp(x).
        x < 100 is the hard-corded criterion.
        Otherwise just set 0.

        """
        irgp = self._grid_points[i_gp]
        freqs = self._frequencies[irgp] * THzToEv
        cutoff = self._pp.cutoff_frequency * THzToEv

        for i_temp, temp in enumerate(self._temperatures):
            if (freqs / (temp * Kb) > 100).any():
                continue
            cvm = mode_cv_matrix(temp, freqs, cutoff=cutoff)
            self._cv_mat[i_temp, i_data] = cvm[self._pp.band_indices, :]

    def _set_velocities(self, i_gp, i_data):
        gvm, gv = self._get_gv_matrix(i_gp)
        self._gv_mat[i_data] = gvm
        self._gv[i_data] = gv

    def _get_gv_matrix(self, i_gp):
        """Get group velocity matrix."""
        self._num_sampling_grid_points += self._grid_weights[i_gp]
        irgp = self._grid_points[i_gp]
        self._velocity_obj.run([self._get_qpoint_from_gp_index(irgp)])
        gvm = np.zeros(self._gv_mat.shape[1:], dtype=self._complex_dtype, order="C")
        gv = np.zeros(self._gv.shape[1:], dtype="double", order="C")
        for i in range(3):
            gvm[i] = self._velocity_obj.group_velocity_matrices[
                0, i, self._pp.band_indices, :
            ]
            gv[:, i] = (
                self._velocity_obj.group_velocity_matrices[0, i]
                .diagonal()[self._pp.band_indices]
                .real
            )
        return gvm, gv

    # def _get_gvm_by_gvm(self, i_gp):
    #     q = self._get_qpoint_from_gp_index(self._grid_points[i_gp])
    #     qpoints = [np.dot(r, q) for r in self._point_operations]
    #     self._velocity_obj.run(qpoints)
    #     gvm = self._velocity_obj.group_velocity_matrices
    #     gvm_sum = np.zeros(
    #         (6,) + self._gv_mat.shape[2:], dtype=self._complex_dtype, order="C"
    #     )
