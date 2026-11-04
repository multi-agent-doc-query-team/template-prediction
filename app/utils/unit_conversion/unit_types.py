from __future__ import annotations

import re

TYPE_DIMENSIONS = {
    'gauge_pressure': 'M/LT2', 'stroke_rate': '1/T',
    'volume_ratio_at_source_conditions': '1',
    'volume_flow_at_source_conditions': 'L3/T',
    'angle_gradient': 'A/L', 'slowness': 'T/L', 'volume_per_length': 'L2',
    'length': 'L', 'distance': 'L', 'depth': 'L', 'area': 'L2', 'volume': 'L3',
    'speed': 'L/T', 'velocity': 'L/T', 'rate': 'L/T', 'acceleration': 'L/T2',
    'mass': 'M', 'density': 'M/L3', 'time': 'T', 'temperature': 'K',
    'temperature_interval': 'D', 'pressure': 'M/LT2', 'force': 'LM/T2',
    'torque': 'L2M/T2', 'energy': 'L2M/T2', 'power': 'L2M/T3',
    'volume_flow': 'L3/T', 'mass_flow': 'M/T', 'frequency': '1/T',
    'angle': 'A', 'rotational_speed': 'A/T', 'dynamic_viscosity': 'M/LT',
    'kinematic_viscosity': 'L2/T', 'permeability': 'L2', 'resistivity': 'L3M/I2T3',
    'electrical_resistance': 'L2M/I2T3', 'conductivity': 'I2T3/L3M',
    'voltage': 'L2M/IT3', 'electric_current': 'I', 'capacitance': 'I2T4/L2M',
    'illuminance': 'JS/L2', 'dimensionless': '1', 'unitless': '1',
}

DIRECT = {
    '1': 'dimensionless', 'L': 'length', 'L3': 'volume',
    'LM/T2': 'force', 'M': 'mass', 'M/L3': 'density',
    'T': 'time', 'K': 'temperature', 'D': 'temperature_interval',
    'A': 'angle', 'A/T': 'rotational_speed', 'A/L': 'angle_gradient',
    'L/T2': 'acceleration', 'T/L': 'slowness',
    'L3/T': 'volume_flow', 'M/T': 'mass_flow',
    '1/T': 'frequency', 'L2M/T3': 'power',
    'M/LT': 'dynamic_viscosity', 'I': 'electric_current',
    'I2T4/L2M': 'capacitance', 'L2M/I2T3': 'electrical_resistance',
    'I2T3/L3M': 'conductivity', 'L3M/I2T3': 'resistivity',
    'L2M/IT3': 'voltage', 'JS/L2': 'illuminance',
    'I/L': 'magnetic_field_strength', 'M/T3': 'power_per_area',
}

def resolved_type(symbol: str, mapping: dict) -> str:
    if mapping.get('response_type'):
        return mapping['response_type']
    dimension = mapping['dimension']
    name = mapping.get('name', '').casefold()
    if dimension == 'L2':
        if symbol in {'D', 'mD'} or 'darcy' in name or 'permeability' in name:
            return 'permeability'
        if ('litre per' in name or 'cubic ' in name and ' per ' in name
                or 'gallon per' in name or 'barrel per' in name):
            return 'volume_per_length'
        if (re.search(r'\b(square|area)\b', name) or symbol in {'acre','ha','section','b'}
                or re.fullmatch(r'(?:[a-zA-Z]+)2', symbol)):
            return 'area'
    if dimension == 'L2M/T2':
        if ('torque' in name or 'foot pound-force' in name
                or 'newton metre' in name or 'newton meter' in name
                or 'pound-force foot' in name or 'pound-force inch' in name
                or 'gram-force metre' in name):
            return 'torque'
        if (symbol in {'J', 'Btu[IT]', 'Btu[th]', 'Btu[UK]', 'erg', 'eV', 'therm[US]', 'therm[UK]', 'therm[EC]', 'quad'}
                or 'joule' in name or 'energy' in name or 'calorie' in name
                or 'btu' in name or 'electron volt' in name or 'electronvolt' in name
                or 'watt hour' in name or 'horsepower hour' in name):
            return 'energy'
    if dimension == 'M/LT2':
        if ('pressure' in name or 'pascal' in name
                or ('water' in name or 'mercury' in name) and any(x in name for x in ('inch', 'centimetre', 'millimetre', 'micrometre'))
                or re.search(r'\bbar\b|\batmosphere\b|\bpsi\b|\btorr\b', name)
                or 'force per square' in name or 'newton per square' in name
                or 'dyne per square' in name):
            return 'pressure'
    if dimension == 'L2/T':
        if 'viscosity' in name or 'stokes' in name:
            return 'kinematic_viscosity'
    if dimension == 'L/T':
        return 'speed'
    if dimension in DIRECT:
        return DIRECT[dimension]
    return f'dimension:{dimension}'
