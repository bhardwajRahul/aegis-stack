"""
Finance Service Detail Modal

A Quicken-style finance workspace, organised into tabs:

* **Accounts** — the register. A left sidebar lists accounts grouped into
  Banking / Credit / Investments / etc., each with its balance and a grand
  total; selecting one shows an account-detail header (with a Manage menu)
  above its transactions (or holdings, for investment accounts). The sidebar
  only lives on this tab.
* **Overview** — a net-worth summary (assets, liabilities, net worth) with a
  per-group breakdown. No sidebar; this is the "home" landing.

Data is fetched async through the internal ``APIClient`` (never a DB session
from the frontend). All colours, spacing, and type come from ``AegisTheme``.
"""

import asyncio

import flet as ft

from app.components.frontend.controls import (
    ConfirmDialog,
    DataTable,
    DataTableColumn,
    ExpandArrow,
    H3Text,
    Tag,
)
from app.components.frontend.controls.buttons import PulseButton
from app.components.frontend.controls.form_fields import FormDropdown, FormTextField
from app.components.frontend.controls.snack_bar import ErrorSnackBar, SuccessSnackBar
from app.components.frontend.controls.table import TableCellText, TableNameText
from app.components.frontend.theme import AegisTheme as Theme
from app.core.config import settings
from app.services.system.models import ComponentStatus
from app.services.system.ui import get_component_title

from ..cards.card_utils import get_status_detail
from .base_detail_popup import BaseDetailPopup
from .modal_sections import (
    EmptyStatePlaceholder,
    LineChartCard,
    LineSeries,
    MetricCard,
)

_SIDEBAR_WIDTH = 320

# account_type -> display group, in sidebar order (Quicken-style buckets).
_ACCOUNT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Banking", ("checking", "savings", "cash")),
    ("Credit Cards", ("credit_card",)),
    ("Investments", ("investment", "brokerage", "crypto")),
    ("Property", ("property", "vehicle")),
    ("Loans & Debt", ("loan", "other_liability")),
    ("Other", ("other_asset",)),
)


def _group_for(account_type: str) -> str:
    for label, types in _ACCOUNT_GROUPS:
        if account_type in types:
            return label
    return "Other"


# Account types whose detail view is holdings (positions), not transactions.
_INVESTMENT_TYPES = frozenset({"brokerage", "investment", "crypto"})

# Curated (account_type, label) choices for the manual "Add account" form. Keys
# are the DB-constrained account_type values; classification is derived below.
_ADD_ACCOUNT_TYPES: tuple[tuple[str, str], ...] = (
    ("checking", "Checking"),
    ("savings", "Savings"),
    ("cash", "Cash"),
    ("credit_card", "Credit card"),
    ("loan", "Loan"),
    ("brokerage", "Brokerage"),
    ("crypto", "Crypto"),
    ("property", "Property"),
    ("vehicle", "Vehicle"),
    ("other_asset", "Other asset"),
    ("other_liability", "Other liability"),
)
_LIABILITY_ACCOUNT_TYPES = frozenset({"credit_card", "loan", "other_liability"})


def _parse_dollars(text: str) -> int:
    """Dollars string -> integer cents. Tolerates ``$``, commas, and blanks."""
    cleaned = (text or "").replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        return round(float(cleaned) * 100)
    except ValueError:
        return 0


def _refresh_row(on_refresh, tooltip: str) -> ft.Control:
    """A right-aligned refresh icon-button, matching the pattern used by the
    other dashboard tabs. Flet holds UI state server-side, so a browser refresh
    won't re-fetch — this button re-pulls the data on demand."""
    return ft.Row(
        [
            ft.Container(expand=True),
            ft.IconButton(
                icon=ft.Icons.REFRESH,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                tooltip=tooltip,
                on_click=on_refresh,
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )


def _usd(cents: int | None) -> str:
    value = (cents or 0) / 100
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _qty(shares: float | None) -> str:
    """Format a share quantity, trimming trailing zeros (10, 2.5, 0.125)."""
    return f"{float(shares or 0):g}"


def _account_display_balance(account: dict) -> int:
    """The balance to show for an account.

    Prefer the authoritative ``current_balance`` (Plaid/statement/valuation);
    for liabilities that figure is the amount owed, so show it negative. Fall
    back to the transaction-sum ``activity_balance`` when no balance is set
    (e.g. a CSV import with no running balance).
    """
    current = account.get("current_balance")
    if current is not None:
        if account.get("classification") == "liability":
            return -abs(current)
        return current
    return account.get("activity_balance") or 0


def _balance_color(cents: int | None) -> str:
    """Teal for positive, red for negative, muted for zero/unknown."""
    value = cents or 0
    if value > 0:
        return Theme.Colors.SUCCESS  # brand teal
    if value < 0:
        return Theme.Colors.ERROR
    return Theme.Colors.TEXT_SECONDARY


def _amount_cell(cents: int) -> ft.Control:
    """Right-aligned, monospaced money — teal for inflow, red for outflow."""
    return ft.Text(
        _usd(cents),
        color=_balance_color(cents),
        size=Theme.Typography.BODY_SMALL,
        weight=ft.FontWeight.W_500,
        font_family="monospace",
        text_align=ft.TextAlign.RIGHT,
    )


def _type_label(account_type: str | None) -> str:
    return (account_type or "account").replace("_", " ").upper()


class AccountsSidebar(ft.Container):
    """Grouped, clickable account list. Calls ``on_select(account | None)`` with
    the full account dict (``None`` for the "All Accounts" row)."""

    def __init__(self, page: ft.Page, on_select) -> None:
        super().__init__()
        self.page = page
        self._on_select = on_select
        self.width = _SIDEBAR_WIDTH
        self.bgcolor = Theme.Colors.SURFACE_1
        self.border = ft.border.only(right=ft.BorderSide(1, Theme.Colors.BORDER_SUBTLE))
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.SM)
        self._list = ft.Column(spacing=3, scroll=ft.ScrollMode.AUTO, expand=True)
        actions: list[ft.Control] = [
            PulseButton(
                on_click_callable=self._open_add_account,
                text="Add account",
                variant="teal",
                compact=True,
            )
        ]
        # "Connect a bank" only when Plaid is configured (the flag/creds exist).
        if getattr(settings, "PLAID_CLIENT_ID", None):
            actions.append(
                PulseButton(
                    on_click_callable=self._connect_bank,
                    text="Connect a bank",
                    variant="amber",
                    compact=True,
                )
            )
        self.content = ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "ACCOUNTS",
                                        size=Theme.Typography.BODY_SMALL,
                                        color=Theme.Colors.TEXT_PRIMARY,
                                        weight=ft.FontWeight.W_600,
                                        expand=True,
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.REFRESH,
                                        icon_color=ft.Colors.ON_SURFACE_VARIANT,
                                        icon_size=18,
                                        tooltip="Refresh accounts",
                                        on_click=lambda e: e.page.run_task(self.reload),
                                    ),
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Row(actions, spacing=Theme.Spacing.SM),
                        ],
                        spacing=Theme.Spacing.SM,
                    ),
                    padding=ft.padding.only(
                        left=Theme.Spacing.MD,
                        right=Theme.Spacing.SM,
                        top=Theme.Spacing.XS,
                        bottom=Theme.Spacing.SM,
                    ),
                ),
                self._list,
            ],
            spacing=0,
            expand=True,
        )
        self._rows: dict[object, ft.Container] = {}
        self._accounts: dict[int, dict] = {}
        self._selected: object = None

    def did_mount(self) -> None:
        if self.page:
            self.page.run_task(self._load)

    def _group_header(self, text: str, subtotal: int) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        text,
                        size=Theme.Typography.CAPTION,
                        color=Theme.Colors.TEXT_SECONDARY,
                        weight=ft.FontWeight.W_600,
                        expand=True,
                    ),
                    ft.Text(
                        _usd(subtotal),
                        size=Theme.Typography.BODY_SMALL,
                        color=_balance_color(subtotal),
                        weight=ft.FontWeight.W_600,
                        font_family="monospace",
                    ),
                ],
                spacing=Theme.Spacing.MD,
            ),
            padding=ft.padding.only(
                left=Theme.Spacing.MD,
                right=Theme.Spacing.MD,
                top=Theme.Spacing.MD,
                bottom=Theme.Spacing.XS,
            ),
        )

    def _row(
        self,
        key: object,
        label: str,
        balance: int | None,
        *,
        indent: int = Theme.Spacing.MD,
        bold: bool = False,
    ) -> ft.Container:
        name = ft.Text(
            label,
            size=Theme.Typography.BODY_SMALL,
            color=Theme.Colors.TEXT_PRIMARY,
            weight=ft.FontWeight.W_600 if bold else ft.FontWeight.W_400,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
        bal = ft.Text(
            _usd(balance) if balance is not None else "",
            size=Theme.Typography.BODY_SMALL,
            color=_balance_color(balance),
            font_family="monospace",
        )
        row = ft.Container(
            content=ft.Row([name, bal], spacing=Theme.Spacing.MD),
            padding=ft.padding.only(
                left=indent,
                right=Theme.Spacing.MD,
                top=Theme.Spacing.SM + 2,
                bottom=Theme.Spacing.SM + 2,
            ),
            border_radius=Theme.Components.BUTTON_RADIUS,
            ink=True,
            data=key,
            on_click=lambda _e, k=key: self._select(k),
            on_hover=self._hover,
        )
        self._rows[key] = row
        return row

    def _hover(self, event: ft.ControlEvent) -> None:
        control = event.control
        if control.data == self._selected:
            return
        control.bgcolor = Theme.Colors.SURFACE_2 if event.data == "true" else None
        control.update()

    def _select(self, key: object) -> None:
        self._selected = key
        for row_key, row in self._rows.items():
            row.bgcolor = Theme.Colors.SURFACE_3 if row_key == key else None
            if row.page is not None:
                row.update()
        account = self._accounts.get(key) if isinstance(key, int) else None
        self._on_select(account)

    async def _load(self, select_id: object = None) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        data = await api.get("/api/v1/finance/accounts", params={"page_size": 200})
        items = data.get("items", []) if isinstance(data, dict) else []

        self._list.controls.clear()
        self._rows.clear()
        self._accounts = {a["id"]: a for a in items}

        total = sum(_account_display_balance(a) for a in items)
        self._list.controls.append(self._row(None, "All Accounts", total, bold=True))

        grouped: dict[str, list] = {}
        for account in items:
            grouped.setdefault(_group_for(account.get("account_type", "")), []).append(
                account
            )
        for label, _types in _ACCOUNT_GROUPS:
            group = grouped.get(label)
            if not group:
                continue
            subtotal = sum(_account_display_balance(a) for a in group)
            self._list.controls.append(self._group_header(label, subtotal))
            for account in sorted(group, key=_account_display_balance, reverse=True):
                self._list.controls.append(
                    self._row(
                        account["id"],
                        account.get("name", ""),
                        _account_display_balance(account),
                    )
                )
        if self._list.page is not None:
            self._list.update()
        # Re-select the requested account if it still exists, else the combined
        # view (used after a rename keeps you where you were; a remove drops you
        # back to All Accounts).
        self._select(select_id if select_id in self._rows else None)

    async def reload(self, select_id: object = None) -> None:
        """Rebuild the list from the API, optionally re-selecting an account."""
        await self._load(select_id=select_id)

    async def _open_add_account(self) -> None:
        """Themed form to create a manual account (name, type, opening balance).
        Classification (asset/liability) is derived from the chosen type."""
        form = {"name": "", "balance": "0"}
        name = FormTextField(
            label="Account name",
            on_change=lambda e: form.__setitem__(
                "name", (getattr(e.control, "value", "") or "").strip()
            ),
            width=360,
        )
        type_dd = FormDropdown(
            label="Type",
            options=list(_ADD_ACCOUNT_TYPES),
            value="checking",
            width=360,
        )
        balance = FormTextField(
            label="Opening balance ($)",
            value="0",
            on_change=lambda e: form.__setitem__(
                "balance", getattr(e.control, "value", "") or ""
            ),
            width=360,
        )

        async def _cancel() -> None:
            self.page.close(dialog)

        async def _add() -> None:
            account_name = form["name"].strip()
            if not account_name:
                ErrorSnackBar("Account name is required.").launch(self.page)
                return
            self.page.close(dialog)
            account_type = type_dd.value or "checking"
            classification = (
                "liability" if account_type in _LIABILITY_ACCOUNT_TYPES else "asset"
            )
            await self._do_add_account(
                name=account_name,
                account_type=account_type,
                classification=classification,
                current_balance=_parse_dollars(form["balance"]),
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=H3Text("Add account"),
            content=ft.Container(
                width=360,
                content=ft.Column(
                    [name, type_dd, balance],
                    spacing=Theme.Spacing.MD,
                    tight=True,
                ),
            ),
            actions=[
                PulseButton(on_click_callable=_cancel, text="Cancel", variant="muted"),
                PulseButton(on_click_callable=_add, text="Add account", variant="teal"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self.page.open(dialog)

    async def _do_add_account(
        self,
        *,
        name: str,
        account_type: str,
        classification: str,
        current_balance: int,
    ) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        result = await api.post(
            "/api/v1/finance/accounts",
            json={
                "name": name,
                "account_type": account_type,
                "classification": classification,
                "current_balance": current_balance,
                "currency": "usd",
            },
        )
        if not isinstance(result, dict) or "id" not in result:
            ErrorSnackBar("Could not add the account.").launch(self.page)
            return
        SuccessSnackBar(f"Added {name}.").launch(self.page)
        await self.reload(select_id=result["id"])

    async def _connect_bank(self) -> None:
        """Plaid Hosted Link: open Plaid's hosted connect page, then poll
        server-side for the result and reload the account list when it lands."""
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        started = await api.post("/api/v1/finance/plaid/hosted-link", json={})
        if not (isinstance(started, dict) and started.get("hosted_link_url")):
            ErrorSnackBar("Could not start Plaid.").launch(self.page)
            return
        self.page.launch_url(started["hosted_link_url"])
        SuccessSnackBar(
            "Complete the connection in the new tab; your accounts will "
            "appear here automatically."
        ).launch(self.page)
        link_token = started["link_token"]
        # Poll for completion (~2.5 min); Plaid hosts the UI, we hold the auth.
        for _ in range(50):
            await asyncio.sleep(3)
            done = await api.post(
                "/api/v1/finance/plaid/hosted-link/complete",
                json={"link_token": link_token},
            )
            if isinstance(done, dict) and done.get("connections", 0) > 0:
                synced = sum(r.get("added", 0) for r in done.get("results", []))
                await self.reload()
                SuccessSnackBar(
                    f"Bank connected — {synced} transactions synced."
                ).launch(self.page)
                return


def _account_detail_header(account: dict, *, on_rename, on_remove) -> ft.Control:
    """The header shown above an account's register: name, type, balance, and a
    Manage menu (Rename always; Remove for manual accounts only — provider
    accounts are owned by the bank connection)."""
    balance = _account_display_balance(account)
    is_manual = account.get("is_manual", False)
    classification = (account.get("classification") or "asset").title()
    source = "Manual" if is_manual else "Connected"
    meta = f"{classification}  ·  {source}  ·  {(account.get('currency') or 'usd').upper()}"

    menu_items = [
        ft.PopupMenuItem(text="Rename", on_click=lambda _e: on_rename(account)),
    ]
    if is_manual:
        menu_items.append(
            ft.PopupMenuItem(text="Remove", on_click=lambda _e: on_remove(account))
        )
    manage = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        tooltip="Manage account",
        items=menu_items,
    )

    left = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        account.get("name", ""),
                        size=Theme.Typography.H3,
                        color=Theme.Colors.TEXT_PRIMARY,
                        weight=ft.FontWeight.W_600,
                    ),
                    Tag(
                        text=_type_label(account.get("account_type")),
                        color=Theme.Colors.INFO,
                    ),
                ],
                spacing=Theme.Spacing.SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(
                meta,
                size=Theme.Typography.CAPTION,
                color=Theme.Colors.TEXT_SECONDARY,
            ),
        ],
        spacing=Theme.Spacing.XS,
        expand=True,
    )
    right = ft.Text(
        _usd(balance),
        size=Theme.Typography.H2,
        color=_balance_color(balance),
        weight=ft.FontWeight.W_700,
        font_family="monospace",
    )
    return ft.Container(
        content=ft.Row(
            [left, right, manage],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(bottom=Theme.Spacing.SM),
    )


class TransactionsPanel(ft.Container):
    """Right-hand detail: the selected account's header + transactions (or
    holdings), with a payee search. ``All Accounts`` shows every transaction."""

    def __init__(self, page: ft.Page) -> None:
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = ft.padding.all(Theme.Spacing.LG)
        self._account: dict | None = None
        self._query = ""
        self._reload_accounts = None  # set by the owner; reloads the sidebar
        self._title = ft.Text(
            "All Accounts",
            size=Theme.Typography.H3,
            color=Theme.Colors.TEXT_PRIMARY,
            weight=ft.FontWeight.W_600,
        )
        self._subtitle = ft.Text(
            "",
            size=Theme.Typography.BODY_SMALL,
            color=Theme.Colors.TEXT_SECONDARY,
        )
        self._search = FormTextField(
            label="Search payee",
            on_change=self._on_change,
            on_submit=self._on_submit,
            width=280,
        )
        # Account-detail header (visible only when a specific account is chosen).
        self._detail = ft.Container(visible=False)
        self._body = ft.Container(expand=True)
        self.content = ft.Column(
            [
                self._detail,
                ft.Row(
                    [
                        ft.Column(
                            [self._title, self._subtitle], spacing=2, expand=True
                        ),
                        self._search,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=Theme.Spacing.MD),
                self._body,
            ],
            spacing=0,
            expand=True,
        )

    def set_reload_hook(self, reload_accounts) -> None:
        """Wire the sidebar's reload coroutine so management actions can refresh
        the account list after a rename/remove."""
        self._reload_accounts = reload_accounts

    def select(self, account: dict | None) -> None:
        self._account = account
        is_account = account is not None
        is_investment = is_account and account.get("account_type") in _INVESTMENT_TYPES
        # The detail header replaces the plain title when an account is chosen.
        self._detail.visible = is_account
        self._detail.content = (
            _account_detail_header(
                account, on_rename=self._open_rename, on_remove=self._open_remove
            )
            if is_account
            else None
        )
        self._title.visible = not is_account
        self._title.value = "All Accounts"
        # Payee search only applies to the transaction view.
        self._search.visible = not is_investment
        self._subtitle.value = ""
        if self._detail.page is not None:
            self._detail.update()
            self._title.update()
            self._subtitle.update()
            self._search.update()
        self.page.run_task(self._load_holdings if is_investment else self._load)

    def _set_subtitle(self, count: int) -> None:
        parts = [f"{count:,} transaction{'s' if count != 1 else ''}"]
        if self._account is None:
            self._subtitle.value = "  ·  ".join(parts)
        else:
            balance = _account_display_balance(self._account)
            parts.append(f"Register balance {_usd(balance)}")
            self._subtitle.value = "  ·  ".join(parts)
        if self._subtitle.page is not None:
            self._subtitle.update()

    def _on_change(self, event: ft.ControlEvent) -> None:
        control = getattr(event, "control", None)
        self._query = (getattr(control, "value", "") or "").strip()

    def _on_submit(self, event: ft.ControlEvent) -> None:
        self._on_change(event)
        self.page.run_task(self._load)

    async def _load(self) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        params: dict[str, object] = {"page_size": 100}
        if self._account is not None:
            params["account_id"] = self._account["id"]
        if self._query:
            params["q"] = self._query
        data = await api.get("/api/v1/finance/transactions", params=params)
        items = data.get("items", []) if isinstance(data, dict) else []
        total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
        self._set_subtitle(total)
        if not items:
            self._body.content = EmptyStatePlaceholder(
                message="No transactions for this account."
            )
            self._refresh()
            return

        columns = [
            DataTableColumn("Date", width=120),
            DataTableColumn("Payee"),
            DataTableColumn("Source", width=90),
            DataTableColumn("Amount", width=150, alignment="right"),
        ]
        rows = [
            [
                TableCellText(str(txn.get("date", ""))),
                TableNameText(txn.get("name") or ""),
                TableCellText(txn.get("source", "")),
                _amount_cell(txn.get("amount", 0)),
            ]
            for txn in items
        ]
        # Wrap the table so the transaction list scrolls independently within
        # the panel (the header + search stay pinned above it).
        self._body.content = ft.Column(
            [DataTable(columns=columns, rows=rows, empty_message="No transactions")],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self._refresh()

    async def _load_holdings(self) -> None:
        """Positions view for an investment account (ticker, qty, price, value)."""
        if self._account is None:
            return
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        data = await api.get(f"/api/v1/finance/accounts/{self._account['id']}/holdings")
        items = data.get("items", []) if isinstance(data, dict) else []
        total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
        portfolio = data.get("portfolio_value", 0) if isinstance(data, dict) else 0
        self._subtitle.value = (
            f"{total:,} holding{'s' if total != 1 else ''}"
            f"  ·  Portfolio value {_usd(portfolio)}"
        )
        if self._subtitle.page is not None:
            self._subtitle.update()
        if not items:
            self._body.content = EmptyStatePlaceholder(
                message="No holdings in this account."
            )
            self._refresh()
            return

        columns = [
            DataTableColumn("Ticker", width=90),
            DataTableColumn("Name"),
            DataTableColumn("Quantity", width=110, alignment="right"),
            DataTableColumn("Price", width=120, alignment="right"),
            DataTableColumn("Market Value", width=150, alignment="right"),
        ]
        rows = [
            [
                TableNameText(holding.get("ticker") or "?"),
                TableCellText(holding.get("name") or ""),
                TableCellText(_qty(holding.get("quantity"))),
                TableCellText(_usd(holding.get("price"))),
                _amount_cell(holding.get("market_value", 0)),
            ]
            for holding in items
        ]
        self._body.content = ft.Column(
            [DataTable(columns=columns, rows=rows, empty_message="No holdings")],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self._refresh()

    def _refresh(self) -> None:
        if self._body.page is not None:
            self._body.update()

    # -- Account management ---------------------------------------------------

    def _open_rename(self, account: dict) -> None:
        value = {"name": account.get("name", "")}
        field = FormTextField(
            label="Account name",
            value=account.get("name", ""),
            on_change=lambda e: value.__setitem__(
                "name", (getattr(e.control, "value", "") or "").strip()
            ),
            width=360,
        )

        async def _cancel() -> None:
            self.page.close(dialog)

        async def _save() -> None:
            self.page.close(dialog)
            new_name = value["name"]
            if new_name and new_name != account.get("name"):
                await self._do_rename(account["id"], new_name)

        # Matches ConfirmDialog styling (SURFACE_CONTAINER_HIGHEST + PulseButtons)
        # but carries a text field, which ConfirmDialog doesn't support.
        dialog = ft.AlertDialog(
            modal=True,
            title=H3Text("Rename account"),
            content=field,
            actions=[
                PulseButton(on_click_callable=_cancel, text="Cancel", variant="muted"),
                PulseButton(on_click_callable=_save, text="Save", variant="teal"),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        )
        self.page.open(dialog)

    def _open_remove(self, account: dict) -> None:
        ConfirmDialog(
            page=self.page,
            title="Remove account",
            message=(
                f'Remove "{account.get("name", "")}"? It will be hidden from '
                "your accounts. Its history is kept and not deleted."
            ),
            confirm_text="Remove",
            destructive=True,
            on_confirm=lambda: self._do_remove(account["id"]),
        ).show()

    async def _do_rename(self, account_id: int, name: str) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        result = await api.patch(
            f"/api/v1/finance/accounts/{account_id}", json={"name": name}
        )
        if not isinstance(result, dict):
            ErrorSnackBar("Could not rename the account.").launch(self.page)
            return
        SuccessSnackBar(f"Renamed to {name}.").launch(self.page)
        if self._reload_accounts is not None:
            await self._reload_accounts(account_id)

    async def _do_remove(self, account_id: int) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        await api.delete(f"/api/v1/finance/accounts/{account_id}")
        SuccessSnackBar("Account removed.").launch(self.page)
        if self._reload_accounts is not None:
            await self._reload_accounts(None)


class AccountsTab(ft.Container):
    """The register tab: account sidebar + transaction/holdings detail."""

    def __init__(self, page: ft.Page) -> None:
        super().__init__()
        self.expand = True
        panel = TransactionsPanel(page)
        sidebar = AccountsSidebar(page, on_select=panel.select)
        panel.set_reload_hook(sidebar.reload)
        self.content = ft.Row([sidebar, panel], spacing=0, expand=True)


def _overview_row(label: str, sublabel: str, amount: int, color: str) -> ft.Control:
    """A labeled amount row for the Overview breakdowns (group totals + spending
    by category). One shape, two callers."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Text(
                    label,
                    size=Theme.Typography.BODY,
                    color=Theme.Colors.TEXT_PRIMARY,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    sublabel,
                    size=Theme.Typography.CAPTION,
                    color=Theme.Colors.TEXT_SECONDARY,
                ),
                ft.Text(
                    _usd(amount),
                    size=Theme.Typography.BODY,
                    color=color,
                    weight=ft.FontWeight.W_600,
                    font_family="monospace",
                ),
            ],
            spacing=Theme.Spacing.LG,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(
            vertical=Theme.Spacing.SM, horizontal=Theme.Spacing.MD
        ),
        border=ft.border.only(bottom=ft.BorderSide(1, Theme.Colors.BORDER_SUBTLE)),
    )


class OverviewTab(ft.Container):
    """Net-worth summary: assets, liabilities, net worth, a per-group breakdown,
    and spending by category. No sidebar — this is the landing view."""

    def __init__(self, page: ft.Page) -> None:
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = ft.padding.all(Theme.Spacing.LG)
        self._body = ft.Column(
            spacing=Theme.Spacing.LG, scroll=ft.ScrollMode.AUTO, expand=True
        )
        self.content = ft.Column(
            [
                _refresh_row(lambda e: e.page.run_task(self._load), "Refresh overview"),
                self._body,
            ],
            spacing=0,
            expand=True,
        )

    def did_mount(self) -> None:
        # Load once the tab is on the page, so page is set and update() paints.
        if self.page:
            self.page.run_task(self._load)

    async def _load(self) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        data = await api.get("/api/v1/finance/accounts", params={"page_size": 200})
        items = data.get("items", []) if isinstance(data, dict) else []

        assets = sum(
            _account_display_balance(a)
            for a in items
            if a.get("classification") != "liability"
        )
        liabilities = sum(
            _account_display_balance(a)
            for a in items
            if a.get("classification") == "liability"
        )
        net_worth = assets + liabilities

        # Net-worth trend (materialized daily by the scheduler; empty until it
        # has run against real accounts).
        nw = await api.get("/api/v1/finance/net-worth", params={"days": 90})
        points = nw if isinstance(nw, list) else []
        chart: ft.Control | None = None
        if len(points) >= 2:
            values = [p.get("net_worth_amount", 0) / 100 for p in points]
            chart = LineChartCard(
                title="Net worth over time",
                subtitle=f"last {len(points)} days",
                x_labels=[str(p.get("as_of_date", "")) for p in points],
                series=[
                    LineSeries(
                        label="Net Worth",
                        color=Theme.Colors.SUCCESS,
                        points=[(i, v) for i, v in enumerate(values)],
                        tooltips=[_usd(p.get("net_worth_amount", 0)) for p in points],
                        fill=True,
                        stroke_width=3,
                    )
                ],
                min_y=min(0.0, min(values)),
            )

        cards = ft.Row(
            [
                MetricCard("Assets", _usd(assets), Theme.Colors.SUCCESS),
                MetricCard("Liabilities", _usd(liabilities), Theme.Colors.ERROR),
                MetricCard("Net Worth", _usd(net_worth), _balance_color(net_worth)),
            ],
            spacing=Theme.Spacing.MD,
        )

        # Per-group breakdown (same buckets as the sidebar).
        grouped: dict[str, list] = {}
        for account in items:
            grouped.setdefault(_group_for(account.get("account_type", "")), []).append(
                account
            )
        breakdown_rows: list[ft.Control] = []
        for label, _types in _ACCOUNT_GROUPS:
            group = grouped.get(label)
            if not group:
                continue
            subtotal = sum(_account_display_balance(a) for a in group)
            plural = "s" if len(group) != 1 else ""
            breakdown_rows.append(
                _overview_row(
                    label,
                    f"{len(group)} account{plural}",
                    subtotal,
                    _balance_color(subtotal),
                )
            )

        # Spending by category (last 30 days) — outflows, largest first.
        spending = await api.get("/api/v1/finance/spending", params={"days": 30})
        spend_rows = [
            _overview_row(
                s.get("category", ""), "", s.get("amount", 0), Theme.Colors.ERROR
            )
            for s in (spending if isinstance(spending, list) else [])[:8]
        ]

        self._body.controls.clear()
        self._body.controls.append(cards)
        if chart is not None:
            self._body.controls.append(chart)
        if breakdown_rows:
            self._body.controls.append(
                ft.Text(
                    "By group",
                    size=Theme.Typography.CAPTION,
                    color=Theme.Colors.TEXT_SECONDARY,
                    weight=ft.FontWeight.W_600,
                )
            )
            self._body.controls.append(ft.Column(breakdown_rows, spacing=0))
        elif not items:
            self._body.controls.append(
                EmptyStatePlaceholder(message="No accounts yet.")
            )
        if spend_rows:
            self._body.controls.append(
                ft.Text(
                    "Spending · last 30 days",
                    size=Theme.Typography.CAPTION,
                    color=Theme.Colors.TEXT_SECONDARY,
                    weight=ft.FontWeight.W_600,
                )
            )
            self._body.controls.append(ft.Column(spend_rows, spacing=0))
        if self._body.page is not None:
            self._body.update()


# Connection status -> (display label, colour).
_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "healthy": ("Connected", Theme.Colors.SUCCESS),
    "loading": ("Syncing", Theme.Colors.WARNING),
    "login_required": ("Login required", Theme.Colors.WARNING),
    "pending_expiration": ("Expiring soon", Theme.Colors.WARNING),
    "pending_disconnect": ("Disconnecting", Theme.Colors.WARNING),
    "consent_expired": ("Consent expired", Theme.Colors.ERROR),
    "revoked": ("Disconnected", Theme.Colors.ERROR),
    "error": ("Error", Theme.Colors.ERROR),
    "manual": ("Manual", Theme.Colors.TEXT_SECONDARY),
}


def _status_style(status: str) -> tuple[str, str]:
    return _STATUS_STYLE.get(
        status, (status.replace("_", " ").title(), Theme.Colors.TEXT_SECONDARY)
    )


def _connection_title(conn: dict) -> str:
    if conn.get("label"):
        return conn["label"]
    provider = (conn.get("provider") or "connection").title()
    environment = (conn.get("environment") or "").title()
    return f"{provider} · {environment}" if environment else provider


# Connection cards lay out in a wrapping grid so account rows stay a comfortable
# ledger width instead of stretching across the whole (1600px) modal.
_CONNECTION_CARD_WIDTH = 680


# Plaid sandbox test credentials (public, from Plaid's sandbox docs). Surfaced
# in the Connections tab only when PLAID_ENV is "sandbox", so you know what to
# type into Plaid's hosted connect screen while testing.
_PLAID_SANDBOX_CREDENTIALS: tuple[tuple[str, str], ...] = (
    ("Username", "user_good"),
    ("Password", "pass_good"),
    ("Phone", "+1 415 555 0011"),
    ("OTP code", "123456"),
    ("Security answer", "1234"),
)


def _sandbox_credentials_card(page: ft.Page) -> ft.Control:
    """Read-only helper panel: Plaid's sandbox test credentials, each with a
    copy button. Only shown when the connection is running in sandbox mode."""

    def _copy(value: str):
        def handler(_e: ft.ControlEvent) -> None:
            page.set_clipboard(value)
            SuccessSnackBar("Copied to clipboard").launch(page)

        return handler

    rows: list[ft.Control] = [
        ft.Row(
            [
                ft.Text(
                    label,
                    size=Theme.Typography.CAPTION,
                    color=Theme.Colors.TEXT_SECONDARY,
                    width=120,
                ),
                ft.Text(
                    value,
                    size=Theme.Typography.BODY_SMALL,
                    color=Theme.Colors.TEXT_PRIMARY,
                    font_family="monospace",
                    selectable=True,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.COPY,
                    icon_size=14,
                    icon_color=Theme.Colors.TEXT_SECONDARY,
                    tooltip=f"Copy {label.lower()}",
                    on_click=_copy(value),
                ),
            ],
            spacing=Theme.Spacing.SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        for label, value in _PLAID_SANDBOX_CREDENTIALS
    ]
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Sandbox test credentials",
                            size=Theme.Typography.BODY,
                            color=Theme.Colors.TEXT_PRIMARY,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                        ),
                        Tag(text="SANDBOX", color=Theme.Colors.WARNING),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(
                    "Enter these in Plaid's connect screen. Sandbox only.",
                    size=Theme.Typography.CAPTION,
                    color=Theme.Colors.TEXT_SECONDARY,
                ),
                ft.Container(height=Theme.Spacing.XS),
                *rows,
            ],
            spacing=Theme.Spacing.XS,
        ),
        width=_CONNECTION_CARD_WIDTH,
        padding=ft.padding.all(Theme.Spacing.MD),
        bgcolor=Theme.Colors.SURFACE_1,
        border=ft.border.all(1, Theme.Colors.BORDER_SUBTLE),
        border_radius=Theme.Components.CARD_RADIUS,
    )


class ConnectionsTab(ft.Container):
    """See every account and how it's connected, and disconnect at any time.

    One card per provider connection (its accounts nested inside, with a
    Disconnect button); a final "Manual & imported" card for accounts that have
    no connection."""

    def __init__(self, page: ft.Page) -> None:
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = ft.padding.all(Theme.Spacing.LG)
        self._body = ft.Column(
            spacing=Theme.Spacing.MD, scroll=ft.ScrollMode.AUTO, expand=True
        )
        self.content = ft.Column(
            [
                _refresh_row(
                    lambda e: e.page.run_task(self._load),
                    "Refresh connections",
                ),
                self._body,
            ],
            spacing=0,
            expand=True,
        )

    def did_mount(self) -> None:
        if self.page:
            self.page.run_task(self._load)

    def _card(
        self,
        title: str,
        accounts: list[dict],
        *,
        status: str | None = None,
        subtitle: str | None = None,
        on_disconnect=None,
    ) -> ft.Control:
        # Aligned columns (Account / Type / Balance) — same DataTable the
        # Accounts tab uses for transactions, so the type reads as a quiet
        # column instead of a loud per-row pill.
        columns = [
            DataTableColumn("Account"),
            DataTableColumn("Type", width=120),
            DataTableColumn("Balance", width=130, alignment="right"),
        ]
        rows = [
            [
                TableNameText(account.get("name", "")),
                TableCellText(
                    (account.get("account_type") or "").replace("_", " ").title()
                ),
                _amount_cell(_account_display_balance(account)),
            ]
            for account in accounts
        ]
        # Collapsible: the account table lives in a container the header toggles.
        arrow = ExpandArrow(expanded=True)
        table = ft.Container(
            content=DataTable(
                columns=columns, rows=rows, empty_message="No accounts."
            ),
            visible=True,
        )

        def _toggle(_e: ft.ControlEvent) -> None:
            arrow.toggle()
            table.visible = arrow.expanded
            arrow.update()
            table.update()

        title_col = ft.Column(
            [
                ft.Text(
                    title,
                    size=Theme.Typography.BODY,
                    color=Theme.Colors.TEXT_PRIMARY,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    subtitle or "",
                    size=Theme.Typography.CAPTION,
                    color=Theme.Colors.TEXT_SECONDARY,
                ),
            ],
            spacing=2,
            expand=True,
        )
        # Clicking the arrow/title toggles; the Disconnect button stays separate.
        header_bits: list[ft.Control] = [
            ft.Container(
                content=ft.Row(
                    [arrow, title_col],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=Theme.Spacing.XS,
                ),
                on_click=_toggle,
                ink=True,
                expand=True,
                border_radius=Theme.Components.BUTTON_RADIUS,
            )
        ]
        if status is not None:
            label, color = _status_style(status)
            header_bits.append(Tag(text=label, color=color))
        if on_disconnect is not None:
            header_bits.append(
                PulseButton(
                    on_click_callable=on_disconnect,
                    text="Disconnect",
                    variant="stop",
                    compact=True,
                )
            )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        header_bits,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    table,
                ],
                spacing=Theme.Spacing.SM,
            ),
            width=_CONNECTION_CARD_WIDTH,
            padding=ft.padding.all(Theme.Spacing.MD),
            bgcolor=Theme.Colors.SURFACE_1,
            border=ft.border.all(1, Theme.Colors.BORDER_SUBTLE),
            border_radius=Theme.Components.CARD_RADIUS,
        )

    async def _load(self) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        conn_data = await api.get("/api/v1/finance/connections")
        acct_data = await api.get("/api/v1/finance/accounts", params={"page_size": 200})
        connections = conn_data.get("items", []) if isinstance(conn_data, dict) else []
        accounts = acct_data.get("items", []) if isinstance(acct_data, dict) else []

        by_connection: dict[int, list[dict]] = {}
        unconnected: list[dict] = []
        for account in accounts:
            cid = account.get("connection_id")
            if cid is None:
                unconnected.append(account)
            else:
                by_connection.setdefault(cid, []).append(account)

        cards: list[ft.Control] = []
        for conn in connections:
            conn_accounts = by_connection.get(conn["id"], [])
            synced = conn.get("last_successful_sync_at")
            synced_text = (
                f"Last synced {str(synced).split('T')[0]}" if synced else "Never synced"
            )
            subtitle = (
                f"{len(conn_accounts)} account"
                f"{'s' if len(conn_accounts) != 1 else ''}  ·  {synced_text}"
            )
            cards.append(
                self._card(
                    _connection_title(conn),
                    conn_accounts,
                    status=conn.get("status"),
                    subtitle=subtitle,
                    on_disconnect=self._disconnect_handler(conn, len(conn_accounts)),
                )
            )

        if unconnected:
            cards.append(
                self._card(
                    "Manual & imported",
                    unconnected,
                    subtitle="Not connected — added manually or from a file import.",
                )
            )

        self._body.controls.clear()
        # Sandbox helper: show Plaid's test credentials when connecting isn't
        # against a real institution.
        if (
            getattr(settings, "PLAID_CLIENT_ID", None)
            and getattr(settings, "PLAID_ENV", "sandbox") == "sandbox"
        ):
            self._body.controls.append(_sandbox_credentials_card(self.page))
        if cards:
            self._body.controls.append(
                ft.Row(
                    cards,
                    wrap=True,
                    spacing=Theme.Spacing.MD,
                    run_spacing=Theme.Spacing.MD,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
        else:
            self._body.controls.append(
                EmptyStatePlaceholder(message="No accounts or connections yet.")
            )
        if self._body.page is not None:
            self._body.update()

    def _disconnect_handler(self, conn: dict, account_count: int):
        """An async no-arg click handler (PulseButton's contract) that opens the
        disconnect confirmation for this connection."""

        async def _handler() -> None:
            self._open_disconnect(conn, account_count)

        return _handler

    def _open_disconnect(self, conn: dict, account_count: int) -> None:
        noun = f"{account_count} account{'s' if account_count != 1 else ''}"
        ConfirmDialog(
            page=self.page,
            title="Disconnect",
            message=(
                f"Disconnect {_connection_title(conn)}? This removes {noun} and "
                "stops syncing. Transaction history is kept and not deleted."
            ),
            confirm_text="Disconnect",
            destructive=True,
            on_confirm=lambda: self._do_disconnect(conn["id"]),
        ).show()

    async def _do_disconnect(self, connection_id: int) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        await api.delete(f"/api/v1/finance/connections/{connection_id}")
        SuccessSnackBar("Disconnected.").launch(self.page)
        await self._load()


class FinanceDetailDialog(BaseDetailPopup):
    """Finance detail modal — a tabbed workspace (Accounts, Connections,
    Overview)."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[
                ft.Tab(text="Accounts", content=AccountsTab(page)),
                ft.Tab(text="Connections", content=ConnectionsTab(page)),
                ft.Tab(text="Overview", content=OverviewTab(page)),
            ],
            expand=True,
            label_color=ft.Colors.ON_SURFACE,
            unselected_label_color=ft.Colors.ON_SURFACE_VARIANT,
            indicator_color=ft.Colors.ON_SURFACE_VARIANT,
        )
        super().__init__(
            page=page,
            component_data=component_data,
            title_text=get_component_title("service_finance"),
            subtitle_text="Accounts, transactions, and investments",
            sections=[tabs],
            scrollable=False,
            width=1600,
            height=900,
            status_detail=get_status_detail(component_data),
        )
