ALIASES = {
    'FT': ('ft', 1),
    '1000 lbm': ('klbm', 1), '10000N': ('N', 10000),
    '1000lbf': ('klbf', 1), 'In': ('in', 1), 'RPM': ('rpm', 1),
    'Kft.lbf': ('lbf.ft', 1000), 'kft.lbf': ('lbf.ft', 1000),
    'ft.klbf': ('lbf.ft', 1000), 'klbf.ft': ('lbf.ft', 1000),
    'ft.lbf': ('lbf.ft', 1), 'kft.klbf': ('lbf.ft', 1000000),
    'deg/100ft': ('0.01 dega/ft', 1), 'dega/100ft': ('0.01 dega/ft', 1),
    'dega/30m': ('dega/m', 1/30), 'ft/hr': ('ft/h', 1),
    'g/cc': ('g/cm3', 1), 'g/sec': ('g/s', 1),
    'galUS/min': ('gal[US]/min', 1), 'hr': ('h', 1),
    'in/64': ('in', 1/64), 'kgm3': ('kg/m3', 1),
    'kkgf': ('kgf', 1000), 'l/sec': ('L/s', 1),
    'lbm/galUS': ('lbm/gal[US]', 1), 'm/hr': ('m/h', 1),
    'm/sec': ('m/s', 1), 'mho/m': ('S/m', 1), 'mmho/m': ('mS/m', 1),
    'sec': ('s', 1), 'seconds': ('s', 1),
    'tonUK': ('ton[UK]', 1), 'tonUS': ('ton[US]', 1), 'tonne': ('t', 1),
    'usec/ft': ('us/ft', 1), 'v/v': ('Euc', 1), 'V/V': ('Euc', 1),

    '64th': ('1/64 in', 1), 'ppg': ('lbm/gal[US]', 1),
    'c/min': ('rpm', 1), 'spm': ('Hz', 1/60),
    'klb': ('klbf', 1), 'kft lb': ('lbf.ft', 1000),
    'bbl/m': ('bbl/min', 1), 'psig': ('psi', 1),

    'SCF/BBL': ('Euc', 0.3048**3 / 0.158987294928),
    'scf/bbl': ('Euc', 0.3048**3 / 0.158987294928),
    'BBL/MMScf': ('Euc', 0.158987294928 / (1e6 * 0.3048**3)),
    'MSCF/d': ('m3/s', 1000 * 0.3048**3 / 86400),
}

RESPONSE_TYPES = {
    'psig': 'gauge_pressure', 'spm': 'stroke_rate',
    'SCF/BBL': 'volume_ratio_at_source_conditions',
    'scf/bbl': 'volume_ratio_at_source_conditions',
    'BBL/MMScf': 'volume_ratio_at_source_conditions',
    'MSCF/d': 'volume_flow_at_source_conditions',
}

PASSTHROUGH = {'DateTime', 'date time', 'datetime', 'NONE'}

UNRESOLVED = {
    '$/m': 'Currency has no physical SI equivalent; currency identity is also unspecified.',
    'gAPI': 'API gamma-ray response requires instrument calibration; no generic SI formula.',
    'gpm': 'US or Imperial gallon is unspecified.',
    'InW': 'Water-column pressure requires the reference temperature and definition.',
    'klft.lbf': 'Unrecognized klft component; cannot silently correct a possible typo.',
    'mft': 'Could mean millifoot or an industry thousand-foot abbreviation.',
    'kdn': 'Unresolved force abbreviation; no verified definition.',
    'mmo': 'Unresolved conductance/conductivity abbreviation and length denominator.',
}
for _symbol in ('lb/mmscf', 'stb/mmscfd'):
    UNRESOLVED[_symbol] = 'Standard-volume reference conditions and abbreviation scale must be established.'

CATEGORY_ALIASES = {
    'rotary_speed': 'rotational_speed', 'rotary_torque': 'torque',
    'mud_flow': 'volume_flow', 'flow_rate': 'volume_flow',
    'volume_rate': 'volume_flow', 'volumerate': 'volume_flow', 'gasrate': 'volume_flow',
    'pit_volume': 'volume', 'bit_diameter': 'length', 'choke_size': 'length',
    'gb_choke_size': 'length', 'tot_fluid_area': 'area',
    'drill_rate': 'speed', 'formation_dens': 'density', 'mud_density': 'density',
    'mud_conductivity': 'conductivity', 'mud_conductiv': 'conductivity',
    'mud_conduct': 'conductivity', 'activity_time': 'time', 'connection_time': 'time',
    'diff_pressure': 'pressure', 'weights': 'mass', 'wirelens_tens': 'force',
    'pump_rate': 'frequency', 'dogleg_severity': 'angle_gradient',
    'sonic_rate': 'slowness', 'volume/length': 'volume_per_length',
    'volume_ratio': 'dimensionless',
    'gas_oil_ratio': 'dimensionless',
}

def extend_mappings(base: dict[str, dict]) -> dict[str, dict]:
    mappings = {symbol: dict(row) for symbol, row in base.items()}
    for alias, (canonical, _) in ALIASES.items():
        if alias in mappings:
            raise ValueError(f'Alias would overwrite an existing definition: {alias}')
        row = dict(base[canonical])
        if row['status'] != 'validated':
            raise ValueError(f'Alias target is not validated: {canonical}')
        row['canonical_unit'] = canonical
        if alias in RESPONSE_TYPES:
            row['response_type'] = RESPONSE_TYPES[alias]
        mappings[alias] = row
    for symbol, reason in UNRESOLVED.items():
        if symbol not in mappings or mappings[symbol]['status'] != 'validated':
            mappings[symbol] = {'status': 'unsupported', 'reason': reason}
    for symbol in PASSTHROUGH:
        mappings[symbol] = {
            'status': 'passthrough', 'target_unit': symbol,
            'response_type': 'passthrough',
        }
    return mappings
