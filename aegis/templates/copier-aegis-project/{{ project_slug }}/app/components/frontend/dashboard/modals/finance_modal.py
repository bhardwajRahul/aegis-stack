"""
Finance Service Detail Modal

A Quicken-style account register: a left sidebar lists accounts grouped into
Assets / Liabilities, each with its register balance (the sum of imported
transactions). Selecting an account loads its transactions in the right panel.

Data is fetched async through the internal ``APIClient`` (never a DB session
from the frontend). All colours, spacing, and type come from ``AegisTheme``.
"""

import flet as ft
from app.components.frontend.controls import DataTable, DataTableColumn
from app.components.frontend.controls.form_fields import FormTextField
from app.components.frontend.controls.table import TableCellText, TableNameText
from app.components.frontend.theme import AegisTheme as Theme
from app.services.system.models import ComponentStatus
from app.services.system.ui import get_component_title

from ..cards.card_utils import get_status_detail
from .base_detail_popup import BaseDetailPopup
from .modal_sections import EmptyStatePlaceholder

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


def _usd(cents: int | None) -> str:
    value = (cents or 0) / 100
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


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


class AccountsSidebar(ft.Container):
    """Grouped, clickable account list. Calls ``on_select(account_id, name,
    balance)`` — ``account_id`` is None for the "All Accounts" row."""

    def __init__(self, page: ft.Page, on_select) -> None:
        super().__init__()
        self.page = page
        self._on_select = on_select
        self.width = _SIDEBAR_WIDTH
        self.bgcolor = Theme.Colors.SURFACE_1
        self.border = ft.border.only(
            right=ft.BorderSide(1, Theme.Colors.BORDER_SUBTLE)
        )
        self.padding = ft.padding.symmetric(vertical=Theme.Spacing.SM)
        self._list = ft.Column(spacing=3, scroll=ft.ScrollMode.AUTO, expand=True)
        self.content = ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "ACCOUNTS",
                        size=Theme.Typography.BODY_SMALL,
                        color=Theme.Colors.TEXT_PRIMARY,
                        weight=ft.FontWeight.W_600,
                    ),
                    padding=ft.padding.only(
                        left=Theme.Spacing.MD,
                        right=Theme.Spacing.MD,
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
        self._selected: object = None
        page.run_task(self._load)

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
            on_click=lambda _e, k=key, ll=label, b=balance: self._select(k, ll, b),
            on_hover=self._hover,
        )
        self._rows[key] = row
        return row

    def _hover(self, event: ft.ControlEvent) -> None:
        control = event.control
        if control.data == self._selected:
            return
        control.bgcolor = (
            Theme.Colors.SURFACE_2 if event.data == "true" else None
        )
        control.update()

    def _select(self, key: object, label: str, balance: int | None) -> None:
        self._selected = key
        for row_key, row in self._rows.items():
            row.bgcolor = (
                Theme.Colors.SURFACE_3 if row_key == key else None
            )
            if row.page is not None:
                row.update()
        self._on_select(key, label, balance)

    async def _load(self) -> None:
        from app.components.frontend.state.session_state import get_session_state

        api = get_session_state(self.page).api_client
        data = await api.get("/api/v1/finance/accounts", params={"page_size": 200})
        items = data.get("items", []) if isinstance(data, dict) else []

        self._list.controls.clear()
        self._rows.clear()

        total = sum((a.get("activity_balance") or 0) for a in items)
        self._list.controls.append(
            self._row(None, "All Accounts", total, bold=True)
        )

        grouped: dict[str, list] = {}
        for account in items:
            grouped.setdefault(
                _group_for(account.get("account_type", "")), []
            ).append(account)
        for label, _types in _ACCOUNT_GROUPS:
            group = grouped.get(label)
            if not group:
                continue
            subtotal = sum((a.get("activity_balance") or 0) for a in group)
            self._list.controls.append(self._group_header(label, subtotal))
            for account in sorted(
                group,
                key=lambda a: a.get("activity_balance") or 0,
                reverse=True,
            ):
                self._list.controls.append(
                    self._row(
                        account["id"],
                        account.get("name", ""),
                        account.get("activity_balance") or 0,
                    )
                )
        self._list.update()
        # Open on the combined view.
        self._select(None, "All Accounts", total)


class TransactionsPanel(ft.Container):
    """Right-hand detail: the selected account's transactions with a search."""

    def __init__(self, page: ft.Page) -> None:
        super().__init__()
        self.page = page
        self.expand = True
        self.padding = ft.padding.all(Theme.Spacing.LG)
        self._account_id: int | None = None
        self._balance: int | None = None
        self._query = ""
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
        self._body = ft.Container(expand=True)
        self.content = ft.Column(
            [
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

    def select(self, account_id: int | None, label: str, balance: int | None) -> None:
        self._account_id = account_id
        self._balance = balance
        self._title.value = label
        self._subtitle.value = (
            f"Register balance {_usd(balance)}" if balance is not None else ""
        )
        if self._title.page is not None:
            self._title.update()
            self._subtitle.update()
        self.page.run_task(self._load)

    def _set_subtitle(self, count: int) -> None:
        parts = [f"{count:,} transaction{'s' if count != 1 else ''}"]
        if self._balance is not None:
            parts.append(f"Register balance {_usd(self._balance)}")
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
        if self._account_id is not None:
            params["account_id"] = self._account_id
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

    def _refresh(self) -> None:
        if self._body.page is not None:
            self._body.update()


class FinanceDetailDialog(BaseDetailPopup):
    """Finance detail modal — account sidebar + transactions register."""

    def __init__(self, component_data: ComponentStatus, page: ft.Page) -> None:
        panel = TransactionsPanel(page)
        sidebar = AccountsSidebar(page, on_select=panel.select)
        body = ft.Container(
            content=ft.Row([sidebar, panel], spacing=0, expand=True),
            expand=True,
        )
        super().__init__(
            page=page,
            component_data=component_data,
            title_text=get_component_title("service_finance"),
            subtitle_text="Accounts and transactions",
            sections=[body],
            scrollable=False,
            width=1600,
            height=900,
            status_detail=get_status_detail(component_data),
        )
