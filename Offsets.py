"""Validated CS2 offsets loader for sezzyaep/CS2-OFFSETS.

All data is fetched in one pass from the same repository. Offset feeds may
update independently from a locally installed CS2 build; this loader cannot
confirm that the running executable matches the downloaded schema.
"""
import requests


class Offsets:
    dwEntityList = None
    dwLocalPlayerController = None
    dwLocalPlayerPawn = None
    dwViewMatrix = None
    m_iszPlayerName = None
    m_iHealth = None
    m_ArmorValue = None
    m_iTeamNum = None
    m_lifeState = None
    m_vOldOrigin = None
    m_hPlayerPawn = None
    m_pGameSceneNode = None
    m_pBoneArray = None
    m_pClippingWeapon = None
    dwPlantedC4 = None
    m_flTimerLength = None
    m_bBeingDefused = None
    m_flDefuseLength = None
    m_bBombDefused = None
    m_bHasExploded = None
    m_vecAbsOrigin = None
    loaded = False
    build_number = None
    offset_source = None

    BASE = "https://raw.githubusercontent.com/sezzyaep/CS2-OFFSETS/main/"

    @staticmethod
    def _number(value, name):
        # Different dumpers emit either raw integers or {'offset': integer}.
        if isinstance(value, dict):
            value = value.get('offset')
        if isinstance(value, str):
            value = int(value, 0)
        if type(value) is not int or value < 0:
            raise ValueError(f"Invalid or missing offset {name}: {value!r}")
        return value

    @classmethod
    def load(cls):
        if cls.loaded:
            return
        def fetch(filename):
            response = requests.get(cls.BASE + filename, timeout=12,
                                    headers={'User-Agent': 'CS2ESP-offset-loader/1.0'})
            response.raise_for_status()
            return response.json()

        try:
            offsets = fetch('offsets.json')['client.dll']
            classes = fetch('client_dll.json')['client.dll']['classes']
            try:
                info = fetch('info.json')
            except Exception as info_error:
                info = {}
                print(f"[Offsets] Build metadata unavailable: {info_error}")

            mapping = {
                'dwEntityList': offsets['dwEntityList'],
                'dwLocalPlayerController': offsets['dwLocalPlayerController'],
                'dwLocalPlayerPawn': offsets['dwLocalPlayerPawn'],
                'dwViewMatrix': offsets['dwViewMatrix'],
                'dwPlantedC4': offsets['dwPlantedC4'],
            }
            def field(group, name):
                return classes[group]['fields'][name]

            for dest, group, key in [
                ('m_iszPlayerName', 'CBasePlayerController', 'm_iszPlayerName'),
                ('m_iHealth', 'C_BaseEntity', 'm_iHealth'),
                ('m_ArmorValue', 'C_CSPlayerPawn', 'm_ArmorValue'),
                ('m_iTeamNum', 'C_BaseEntity', 'm_iTeamNum'),
                ('m_lifeState', 'C_BaseEntity', 'm_lifeState'),
                ('m_vOldOrigin', 'C_BasePlayerPawn', 'm_vOldOrigin'),
                ('m_hPlayerPawn', 'CCSPlayerController', 'm_hPlayerPawn'),
                ('m_pGameSceneNode', 'C_BaseEntity', 'm_pGameSceneNode'),
                ('m_flTimerLength', 'C_PlantedC4', 'm_flTimerLength'),
                ('m_bBeingDefused', 'C_PlantedC4', 'm_bBeingDefused'),
                ('m_flDefuseLength', 'C_PlantedC4', 'm_flDefuseLength'),
                ('m_bBombDefused', 'C_PlantedC4', 'm_bBombDefused'),
                ('m_bHasExploded', 'C_PlantedC4', 'm_bHasExploded'),
                ('m_vecAbsOrigin', 'CGameSceneNode', 'm_vecAbsOrigin'),
            ]:
                mapping[dest] = field(group, key)
            mapping['m_pBoneArray'] = cls._number(field('CSkeletonInstance', 'm_modelState'), 'm_modelState') + 128

            validated = {name: cls._number(value, name) for name, value in mapping.items()}
            for name in ('dwEntityList', 'dwLocalPlayerController', 'dwLocalPlayerPawn', 'dwViewMatrix'):
                if not validated[name]:
                    raise ValueError(f"Zero critical offset: {name}")
            for name, val in validated.items():
                setattr(cls, name, val)
            cls.loaded = True
            cls.build_number = info.get('build_number')
            cls.offset_source = 'sezzyaep/CS2-OFFSETS'
            print(f"[Offsets] Source: {cls.offset_source}; build={cls.build_number}; generated={info.get('timestamp', 'unknown')}")
            for name in ('dwEntityList', 'dwLocalPlayerController', 'dwLocalPlayerPawn', 'dwViewMatrix'):
                print(f"[Offsets] {name} = 0x{validated[name]:X}")
            print('[Offsets] WARNING: Confirm that the offset build matches your installed CS2 build.')
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            cls.loaded = False
            raise RuntimeError(f"Failed to load compatible offset data: {exc}") from exc
