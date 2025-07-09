"""
A platform that provides information about the tracking of objects in the post office in Brazil
For more details about this component, please refer to the documentation at
https://github.com/caseca/home-assistant-correios
"""

import logging
import async_timeout
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from correios_api import CorreiosApi

import json
from .const import (
    BASE_API,
    BASE_URL,
    CONF_TRACKING,
    CONF_DESCRIPTION,
    DOMAIN,
    ICON,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensor dynamically."""
    track = entry.data[CONF_TRACKING]
    description = entry.data[CONF_DESCRIPTION]
    session = async_create_clientsession(hass)
    name = f"{description} ({track})"

    async_add_entities(
        [CorreiosSensor(track, entry.entry_id, name, description, session)],
        True,
    )


class CorreiosSensor(SensorEntity):
    def __init__(
        self,
        track,
        config_entry_id,
        name,
        description,
        session,
    ):
        self.session = session
        self.track = track
        self._name = name
        self.description = description
        self._image = None
        self.dtPrevista = None
        self.data_movimentacao = None
        self.origem = None
        self.destino = None
        self.tipoPostal = None
        self._state = None
        self._attr_unique_id = track
        self.trackings = []

        self._attr_device_info = DeviceInfo(
            entry_type=dr.DeviceEntryType.SERVICE,
            config_entry_id=config_entry_id,
            connections=None,
            identifiers={(DOMAIN, track)},
            manufacturer="Correios",
            name=track,
            model="Não aplicável",
            sw_version=None,
            hw_version=None,
        )

    async def async_update(self):
        try:
            def rastreio():
                api = CorreiosApi()
                return api.track(self.track)

            resultado = await self.hass.async_add_executor_job(rastreio)
            if not resultado or "error" in resultado:
                self._state = "Objeto não encontrado"
                self.trackings = []
                return

            eventos = resultado.get("events", [])
            if eventos:
                evento = eventos[0]
                self._state = evento.get("status", "Sem eventos")
                self.data_movimentacao = evento.get("date")
                self.origem = evento.get("unit")
                self.destino = evento.get("destination")
                self.tipoPostal = resultado.get("type")
                self.dtPrevista = resultado.get("forecast")
                self.trackings = [
                    {
                        "Descrição": e.get("status"),
                        "Data/Hora": e.get("date"),
                        "Local": e.get("unit"),
                        "Destino": e.get("destination"),
                    }
                    for e in eventos
                ]
            else:
                self._state = "Sem eventos"
                self.trackings = []
        except Exception as error:
            _LOGGER.error("Não foi possível atualizar - %s", error)

    @property
    def name(self):
        return self._name

    @property
    def entity_picture(self):
        return self._image

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return ICON

    @property
    def extra_state_attributes(self):

        return {
            "Descrição": self.description,
            "Código Objeto": self.track,
            "Data Prevista": self.dtPrevista,
            "Origem": self.origem,
            "Destino": self.destino,
            "Última Movimentação": self.data_movimentacao,
            "Tipo Postal": self.tipoPostal,
            "Movimentações": self.trackings,
        }
