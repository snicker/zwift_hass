"""Config flow for Zwift integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode, SelectOptionDict

from .const import _LOGGER, CONF_INCLUDE_SELF, CONF_PLAYERS, DOMAIN

import custom_components.zwift.zwift_patch  # noqa: F401 — applies protobuf patch
from zwift import Client as ZwiftClient


def _fetch_followees(client):
    """Fetch the list of followees for the authenticated user."""
    profile = client.get_profile()
    followees_data = profile.followees
    results = []
    for f in followees_data:
        # followee entries contain the profile nested under "followeeProfile"
        fp = f.get("followeeProfile", f)
        player_id = str(fp.get("id", ""))
        first = fp.get("firstName", "")
        last = fp.get("lastName", "")
        label = f"{first} {last}".strip() or player_id
        if player_id:
            results.append({"id": player_id, "label": f"{label} ({player_id})"})
    return results


class ZwiftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zwift."""

    VERSION = 1

    def __init__(self):
        self._client = None
        self._user_data = {}
        self._followees = []

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ZwiftOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step — credentials."""
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            try:
                client = ZwiftClient(username, password)
                token = await self.hass.async_add_executor_job(
                    client.auth_token.fetch_token_data
                )
                if "error" in token:
                    errors["base"] = "invalid_auth"
                else:
                    self._client = client
                    self._user_data = {
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    }

                    # Fetch followees for the selection step
                    try:
                        self._followees = await self.hass.async_add_executor_job(
                            _fetch_followees, client
                        )
                    except Exception:
                        _LOGGER.warning("Could not fetch followees list")
                        self._followees = []

                    return await self.async_step_select_players()
            except Exception:
                _LOGGER.exception("Error connecting to Zwift")
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_select_players(self, user_input=None):
        """Let the user pick players from their followees list."""
        if user_input is not None:
            selected = user_input.get(CONF_PLAYERS, [])
            include_self = user_input.get(CONF_INCLUDE_SELF, True)

            return self.async_create_entry(
                title=f"Zwift ({self._user_data[CONF_USERNAME]})",
                data=self._user_data,
                options={
                    CONF_PLAYERS: selected,
                    CONF_INCLUDE_SELF: include_self,
                },
            )

        followee_options = [
            SelectOptionDict(value=f["id"], label=f["label"])
            for f in self._followees
        ]

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_PLAYERS, default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=followee_options,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        custom_value=True,
                    )
                ),
                vol.Optional(CONF_INCLUDE_SELF, default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="select_players",
            data_schema=data_schema,
        )

    async def async_step_import(self, import_data):
        """Handle import from YAML configuration."""
        username = import_data[CONF_USERNAME]
        await self.async_set_unique_id(username.lower())
        self._abort_if_unique_id_configured()

        # Ensure players is a list
        players = import_data.pop(CONF_PLAYERS, [])
        if isinstance(players, str):
            players = [p.strip() for p in players.split(",") if p.strip()]
        include_self = import_data.pop(CONF_INCLUDE_SELF, True)

        return self.async_create_entry(
            title=f"Zwift ({username})",
            data=import_data,
            options={
                CONF_PLAYERS: players,
                CONF_INCLUDE_SELF: include_self,
            },
        )


class ZwiftOptionsFlow(config_entries.OptionsFlow):
    """Handle Zwift options (manage tracked players)."""

    def __init__(self, config_entry):
        self._config_entry = config_entry
        self._followees = []

    async def async_step_init(self, user_input=None):
        """Manage the options — show followees multi-select."""
        if user_input is not None:
            selected = user_input.get(CONF_PLAYERS, [])
            return self.async_create_entry(
                title="",
                data={
                    CONF_PLAYERS: selected,
                    CONF_INCLUDE_SELF: user_input.get(CONF_INCLUDE_SELF, True),
                },
            )

        # Build a client from stored credentials to fetch followees
        username = self._config_entry.data[CONF_USERNAME]
        password = self._config_entry.data[CONF_PASSWORD]
        try:
            client = ZwiftClient(username, password)
            self._followees = await self.hass.async_add_executor_job(
                _fetch_followees, client
            )
        except Exception:
            _LOGGER.warning("Could not fetch followees list for options")
            self._followees = []

        current_players = self._config_entry.options.get(CONF_PLAYERS, [])
        current_include_self = self._config_entry.options.get(CONF_INCLUDE_SELF, True)

        followee_options = [
            SelectOptionDict(value=f["id"], label=f["label"])
            for f in self._followees
        ]

        # Ensure currently tracked players appear even if not in followees
        followee_ids = {f["id"] for f in self._followees}
        for pid in current_players:
            if str(pid) not in followee_ids:
                followee_options.append(
                    SelectOptionDict(value=str(pid), label=f"Player {pid}")
                )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PLAYERS,
                    default=[str(p) for p in current_players],
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=followee_options,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        custom_value=True,
                    )
                ),
                vol.Optional(
                    CONF_INCLUDE_SELF,
                    default=current_include_self,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
