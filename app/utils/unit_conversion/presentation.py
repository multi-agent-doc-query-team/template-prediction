from .dimensions import dimension_terms

NAMED_SI_TARGETS = {
    'gauge_pressure': 'pascal', 'stroke_rate': '1/s',
    'volume_ratio_at_source_conditions': 'm3/m3',
    'volume_flow_at_source_conditions': 'm3/s',
    'length': 'meter', 'mass': 'kilogram', 'time': 'second',
    'temperature': 'kelvin', 'temperature_interval': 'kelvin',
    'force': 'newton', 'pressure': 'pascal', 'power': 'watt',
    'energy': 'joule', 'dimensionless': 'dimensionless',
    'area': 'm2', 'volume': 'm3', 'density': 'kg/m3',
    'speed': 'm/s', 'acceleration': 'm/s2', 'frequency': 'hertz',
    'volume_flow': 'm3/s', 'mass_flow': 'kg/s', 'slowness': 's/m',
    'torque': 'N.m', 'angle': 'radian', 'rotational_speed': 'rad/s',
    'dynamic_viscosity': 'Pa.s', 'kinematic_viscosity': 'm2/s',
    'permeability': 'm2', 'electric_current': 'ampere',
    'voltage': 'volt', 'electrical_resistance': 'ohm',
    'capacitance': 'farad', 'conductivity': 'S/m',
    'resistivity': 'ohm.m', 'illuminance': 'lux',
    'angle_gradient': 'rad/m', 'volume_per_length': 'm2',
    'magnetic_field_strength': 'A/m', 'power_per_area': 'W/m2',
}
SI_BASE_SYMBOLS = {'M': 'kg', 'L': 'm', 'T': 's', 'I': 'A', 'K': 'K',
                   'D': 'K', 'N': 'mol', 'J': 'cd', 'A': 'rad', 'S': 'sr'}
SI_BASE_ORDER = tuple(SI_BASE_SYMBOLS)

def display_target_unit(dimension: str, kind: str) -> str:
    if kind in NAMED_SI_TARGETS:
        return NAMED_SI_TARGETS[kind]
    terms = dimension_terms(dimension)
    if not terms:
        return 'dimensionless'
    def part(letter, power):
        return SI_BASE_SYMBOLS[letter] + (str(power) if power != 1 else '')

    numerator = [part(letter, terms[letter]) for letter in SI_BASE_ORDER if terms.get(letter, 0) > 0]
    denominator = [part(letter, -terms[letter]) for letter in SI_BASE_ORDER if terms.get(letter, 0) < 0]
    left = '.'.join(numerator) or '1'
    if not denominator:
        return left
    right = '.'.join(denominator)
    return f'{left}/({right})' if len(denominator) > 1 else f'{left}/{right}'
