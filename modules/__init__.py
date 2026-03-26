from modules import billing, tickets, contracts, rmm, policy

# Registry — add new modules here as they are built.
# key   : display name shown in the sidebar
# value : module that exposes a render() function
REGISTRY: dict[str, object] = {
    "Billing": billing,
    "Tickets": tickets,
    "Contracts": contracts,
    "RMM": rmm,
    "Policy": policy,
}
