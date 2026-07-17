"""Pruebas unitarias de portfolio/constraints.py: funciones puras, sin red ni Streamlit."""
from __future__ import annotations

import numpy as np
import pytest

import config
from core.capm import is_eligible_for_profile as capm_is_eligible_for_profile
from tests import fixtures_real_universe as real_universe
from portfolio.constraints import (
    InfeasibleConstraintsError,
    ProfileConstraints,
    build_equity_mask,
    build_fixed_income_mask,
    get_constraints_for_profile,
    is_asset_eligible_for_profile,
    validate_constraint_feasibility,
)


def test_get_constraints_for_conservador_matches_specification() -> None:
    constraints = get_constraints_for_profile(config.PERFIL_CONSERVADOR)
    assert constraints.max_weight_per_asset == pytest.approx(0.25)
    assert constraints.min_fixed_income_weight == pytest.approx(0.60)
    assert constraints.max_equity_weight == pytest.approx(0.40)


def test_get_constraints_for_moderado_matches_specification() -> None:
    constraints = get_constraints_for_profile(config.PERFIL_MODERADO)
    assert constraints.max_weight_per_asset == pytest.approx(0.35)
    assert constraints.min_fixed_income_weight == pytest.approx(0.30)
    assert constraints.max_equity_weight == pytest.approx(0.70)


def test_get_constraints_for_agresivo_matches_specification() -> None:
    constraints = get_constraints_for_profile(config.PERFIL_AGRESIVO)
    assert constraints.max_weight_per_asset == pytest.approx(0.45)
    assert constraints.min_fixed_income_weight == pytest.approx(0.10)
    assert constraints.max_equity_weight == pytest.approx(0.90)


def test_get_constraints_raises_for_unknown_profile() -> None:
    with pytest.raises(ValueError, match="No hay restricciones definidas"):
        get_constraints_for_profile("Inexistente")


@pytest.mark.parametrize(
    "profile", [config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO]
)
def test_equity_and_fixed_income_bands_are_complementary(profile: str) -> None:
    """Por diseno, min_fixed_income + max_equity = 100%: no se deja un remanente sin banda."""
    constraints = get_constraints_for_profile(profile)
    assert constraints.min_fixed_income_weight + constraints.max_equity_weight == pytest.approx(1.0)


def test_max_weight_per_asset_increases_with_risk_appetite() -> None:
    conservador = get_constraints_for_profile(config.PERFIL_CONSERVADOR)
    moderado = get_constraints_for_profile(config.PERFIL_MODERADO)
    agresivo = get_constraints_for_profile(config.PERFIL_AGRESIVO)
    assert conservador.max_weight_per_asset < moderado.max_weight_per_asset < agresivo.max_weight_per_asset


def test_min_fixed_income_weight_decreases_with_risk_appetite() -> None:
    conservador = get_constraints_for_profile(config.PERFIL_CONSERVADOR)
    moderado = get_constraints_for_profile(config.PERFIL_MODERADO)
    agresivo = get_constraints_for_profile(config.PERFIL_AGRESIVO)
    assert conservador.min_fixed_income_weight > moderado.min_fixed_income_weight > agresivo.min_fixed_income_weight


# --- Elegibilidad por clase de activo ---


@pytest.mark.parametrize("profile", [config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO])
@pytest.mark.parametrize("beta", [-1.0, 0.0, 0.02, 5.0])
def test_fixed_income_and_money_market_are_always_eligible_regardless_of_beta(profile: str, beta: float) -> None:
    assert is_asset_eligible_for_profile(beta, config.CLASE_RENTA_FIJA, profile) is True
    assert is_asset_eligible_for_profile(beta, config.CLASE_MONETARIO, profile) is True


@pytest.mark.parametrize("profile", [config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO])
@pytest.mark.parametrize("beta", [0.3, 0.75, 1.0, 1.25, 1.8])
def test_equity_eligibility_delegates_unchanged_to_capm(profile: str, beta: float) -> None:
    """'Para acciones sigue siendo correcto': el criterio de Beta no cambia para renta variable."""
    expected = capm_is_eligible_for_profile(beta, profile)
    assert is_asset_eligible_for_profile(beta, config.CLASE_RENTA_VARIABLE, profile) is expected


# --- Mascaras ---


def test_build_fixed_income_mask_marks_only_fixed_income_and_money_market() -> None:
    asset_classes = np.array(
        [config.CLASE_RENTA_VARIABLE, config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO, config.CLASE_RENTA_VARIABLE]
    )
    mask = build_fixed_income_mask(asset_classes)
    np.testing.assert_array_equal(mask, [0.0, 1.0, 1.0, 0.0])


def test_build_equity_mask_marks_only_equity() -> None:
    asset_classes = np.array(
        [config.CLASE_RENTA_VARIABLE, config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO, config.CLASE_RENTA_VARIABLE]
    )
    mask = build_equity_mask(asset_classes)
    np.testing.assert_array_equal(mask, [1.0, 0.0, 0.0, 1.0])


def test_masks_are_complementary_and_cover_the_whole_universe() -> None:
    asset_classes = np.array(
        [config.CLASE_RENTA_VARIABLE, config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO]
    )
    fixed_income_mask = build_fixed_income_mask(asset_classes)
    equity_mask = build_equity_mask(asset_classes)
    np.testing.assert_array_equal(fixed_income_mask + equity_mask, np.ones(len(asset_classes)))


def test_profile_constraints_is_immutable() -> None:
    constraints = ProfileConstraints(
        profile=config.PERFIL_MODERADO, max_weight_per_asset=0.35, min_fixed_income_weight=0.30, max_equity_weight=0.70
    )
    with pytest.raises(AttributeError):
        constraints.max_weight_per_asset = 0.99  # type: ignore[misc]


# --- validate_constraint_feasibility (Subfase 3.4, Parte 2) ---


def test_feasibility_accepts_the_real_13_asset_universe_for_all_profiles() -> None:
    for profile in (config.PERFIL_CONSERVADOR, config.PERFIL_MODERADO, config.PERFIL_AGRESIVO):
        profile_constraints = get_constraints_for_profile(profile)
        validate_constraint_feasibility(real_universe.ASSET_CLASSES, profile_constraints)  # no debe lanzar


def test_feasibility_rejects_insufficient_fixed_income_capacity() -> None:
    """Reproduce el hallazgo de la Subfase 3.3: 2 activos de renta fija/monetario,
    tope de 25% -> 50% maximo, insuficiente para el 60% de Conservador."""
    asset_classes = np.array([config.CLASE_RENTA_VARIABLE] * 9 + [config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO])
    profile_constraints = get_constraints_for_profile(config.PERFIL_CONSERVADOR)
    with pytest.raises(InfeasibleConstraintsError, match="renta fija"):
        validate_constraint_feasibility(asset_classes, profile_constraints)


def test_feasibility_rejects_insufficient_total_capacity() -> None:
    """4 activos con un tope de 20% cada uno solo permiten cubrir el 80% de la cartera:
    no se puede completar el 100% exigido por sum(w)=1, sin importar la clase de activo."""
    asset_classes = np.array(
        [config.CLASE_RENTA_VARIABLE, config.CLASE_RENTA_VARIABLE, config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO]
    )
    restrictive_constraints = ProfileConstraints(
        profile="Prueba", max_weight_per_asset=0.20, min_fixed_income_weight=0.10, max_equity_weight=0.90
    )
    with pytest.raises(InfeasibleConstraintsError, match="capacidad máxima combinada"):
        validate_constraint_feasibility(asset_classes, restrictive_constraints)


def test_feasibility_rejects_contradictory_bands() -> None:
    """min_fixed_income + max_equity < 100% es una contradiccion estructural: ni
    maximizando renta fija ni maximizando renta variable se puede llegar al 100%."""
    asset_classes = np.array([config.CLASE_RENTA_VARIABLE] * 5 + [config.CLASE_RENTA_FIJA] * 5)
    contradictory_constraints = ProfileConstraints(
        profile="Prueba", max_weight_per_asset=0.30, min_fixed_income_weight=0.50, max_equity_weight=0.40
    )
    with pytest.raises(InfeasibleConstraintsError, match="contradictorias"):
        validate_constraint_feasibility(asset_classes, contradictory_constraints)


def test_feasibility_error_message_is_specific_not_a_bare_string_check() -> None:
    """La excepcion debe ser un tipo especifico (capturable con `except InfeasibleConstraintsError`),
    no un ValueError generico ni una cadena suelta devuelta como resultado."""
    asset_classes = np.array([config.CLASE_RENTA_VARIABLE] * 9 + [config.CLASE_RENTA_FIJA, config.CLASE_MONETARIO])
    profile_constraints = get_constraints_for_profile(config.PERFIL_CONSERVADOR)

    assert issubclass(InfeasibleConstraintsError, Exception)
    with pytest.raises(InfeasibleConstraintsError) as exc_info:
        validate_constraint_feasibility(asset_classes, profile_constraints)

    message = str(exc_info.value)
    assert "60%" in message
    assert "50%" in message
    assert config.PERFIL_CONSERVADOR in message
