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
            # pycorreios não é async, então rode em executor
            from pycorreios import rastrear_objeto

            def rastreio():
                return rastrear_objeto(self.track)

            objetos = await self.hass.async_add_executor_job(rastreio)
            if not objetos:
                self._state = "Objeto não encontrado"
                self.trackings = []
                return

            objeto = objetos[0]
            self._state = objeto.eventos[0].descricao if objeto.eventos else "Sem eventos"
            self.data_movimentacao = (
                objeto.eventos[0].data_hora.strftime("%Y-%m-%d %H:%M")
                if objeto.eventos else None
            )
            self.origem = (
                objeto.eventos[0].unidade.nome if objeto.eventos and objeto.eventos[0].unidade else None
            )
            self.destino = (
                objeto.eventos[0].unidade_destino.nome if objeto.eventos and objeto.eventos[0].unidade_destino else None
            )
            self.tipoPostal = objeto.tipo
            self.dtPrevista = None  # pycorreios não retorna data prevista
            self.trackings = [
                {
                    "Descrição": evento.descricao,
                    "Data/Hora": evento.data_hora.strftime("%Y-%m-%d %H:%M"),
                    "Local": evento.unidade.nome if evento.unidade else "",
                    "Destino": evento.unidade_destino.nome if evento.unidade_destino else "",
                }
                for evento in objeto.eventos
            ]
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
