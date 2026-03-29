/**
 * Main layout with top header and accounts sidebar
 */

import {
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Button,
  Badge,
  Spinner,
  Center,
  useDisclosure,
  Avatar,
  Collapse,
  Tooltip,
  useColorModeValue,
} from "@chakra-ui/react";

import {
  AddIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  WarningIcon,
} from "@chakra-ui/icons";
import { FiSettings, FiLogOut, FiUsers } from "react-icons/fi";
import {
  Navigate,
  Outlet,
  useNavigate,
  useLocation,
  useSearchParams,
} from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import { useAuthStore } from "../features/auth/stores/authStore";
import { useLogout } from "../features/auth/hooks/useAuth";
import api from "../services/api";
import { useHouseholdMembers } from "../hooks/useHouseholdMembers";
import { AddAccountModal } from "../features/accounts/components/AddAccountModal";
import NotificationBell from "../features/notifications/components/NotificationBell";
import MilestoneCelebration from "../features/notifications/components/MilestoneCelebration";
import { HouseholdSwitcher } from "./HouseholdSwitcher";
import { useHouseholdStore } from "../stores/householdStore";
import { useShallow } from "zustand/react/shallow";
import { UserViewToggle } from "./UserViewToggle";
import { useUserView } from "../contexts/UserViewContext";
import { EmailVerificationBanner } from "./EmailVerificationBanner";
import { OfflineIndicator } from "./OfflineIndicator";
import { RouteErrorBoundary } from "./RouteErrorBoundary";
import {
  RESOURCE_TYPE_LABELS,
  getBannerAccess,
  getMultiMemberAccess,
  getResourceTypeForPath,
} from "../utils/permissionBannerUtils";
import { ACCOUNT_TYPE_SIDEBAR_CONFIG } from "../constants/accountTypeGroups";
import { useNavDefaults } from "../hooks/useNavDefaults";
import { useNotificationToast } from "../hooks/useNotificationToast";
import { NotificationType, NotificationPriority } from "../types/notification";

interface Account {
  id: string;
  name: string;
  account_type: string;
  current_balance: number;
  balance_as_of: string | null;
  user_id: string;
  plaid_item_hash: string | null;
  plaid_item_id: string | null;
  exclude_from_cash_flow: boolean;
  is_rental_property?: boolean;
  // Sync status
  last_synced_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  needs_reauth: boolean | null;
}

interface DedupedAccount extends Account {
  owner_ids: string[]; // Array of user IDs who own this account
  is_shared: boolean; // True if owned by multiple users
}

interface NavItemProps {
  label: string;
  path: string;
  isActive: boolean;
  onClick: () => void;
}

interface NavDropdownProps {
  label: string;
  items: { label: string; path: string; tooltip?: string }[];
  currentPath: string;
  onNavigate: (path: string) => void;
}

const NavDropdown = ({
  label,
  items,
  currentPath,
  onNavigate,
}: NavDropdownProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isActive = items.some((item) => currentPath === item.path);

  useEffect(() => {
    if (!isOpen) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [isOpen]);

  return (
    <Box position="relative" ref={ref}>
      <Button
        rightIcon={<ChevronDownIcon />}
        variant={isActive ? "solid" : "ghost"}
        colorScheme={isActive ? "brand" : "gray"}
        size="sm"
        fontWeight={isActive ? "semibold" : "medium"}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        {label}
      </Button>
      {isOpen && (
        <Box
          position="absolute"
          top="calc(100% + 4px)"
          left={0}
          bg="bg.surface"
          borderWidth={1}
          borderColor="border.default"
          borderRadius="md"
          boxShadow="md"
          zIndex={200}
          minW="180px"
          py={1}
        >
          {items.map((item) => (
            <Tooltip
              key={item.path}
              label={item.tooltip}
              isDisabled={!item.tooltip}
              placement="right"
              hasArrow
            >
              <Box
                px={3}
                py={2}
                cursor="pointer"
                fontWeight={currentPath === item.path ? "semibold" : "normal"}
                bg={currentPath === item.path ? "brand.subtle" : "transparent"}
                _hover={{
                  bg: currentPath === item.path ? "brand.subtle" : "bg.subtle",
                }}
                fontSize="sm"
                onClick={() => {
                  onNavigate(item.path);
                  setIsOpen(false);
                }}
              >
                {item.label}
              </Box>
            </Tooltip>
          ))}
        </Box>
      )}
    </Box>
  );
};

const UserMenu = ({
  user,
  onNavigate,
  onLogout,
  isMultiMemberHousehold,
}: {
  user: {
    first_name?: string;
    last_name?: string;
    display_name?: string;
    email?: string;
  } | null;
  onNavigate: (path: string) => void;
  onLogout: () => void;
  isMultiMemberHousehold: boolean;
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [isOpen]);

  const menuItems = [
    { label: "Household Settings", icon: <FiUsers />, path: "/household" },
    ...(isMultiMemberHousehold
      ? [
          {
            label: "My Permissions",
            icon: <FiSettings />,
            path: "/permissions",
          },
        ]
      : []),
    { label: "My Preferences", icon: <FiSettings />, path: "/preferences" },
  ];

  return (
    <Box position="relative" ref={ref}>
      <Button
        rightIcon={<ChevronDownIcon />}
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <HStack spacing={2}>
          <Avatar
            size="sm"
            name={
              user?.display_name ||
              `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() ||
              user?.email
            }
            bg="brand.500"
          />
          <VStack align="start" spacing={0}>
            <Text fontSize="sm" fontWeight="medium">
              {user?.display_name ||
                `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() ||
                user?.email}
            </Text>
            <Text fontSize="xs" color="text.secondary">
              {user?.email}
            </Text>
          </VStack>
        </HStack>
      </Button>
      {isOpen && (
        <Box
          position="absolute"
          top="calc(100% + 4px)"
          right={0}
          bg="bg.surface"
          borderWidth={1}
          borderColor="border.default"
          borderRadius="md"
          boxShadow="md"
          zIndex={200}
          minW="180px"
          py={1}
        >
          {menuItems.map((item) => (
            <Box
              key={item.path}
              px={3}
              py={2}
              cursor="pointer"
              _hover={{ bg: "bg.subtle" }}
              fontSize="sm"
              onClick={() => {
                onNavigate(item.path);
                setIsOpen(false);
              }}
            >
              <HStack spacing={2}>
                {item.icon}
                <Text>{item.label}</Text>
              </HStack>
            </Box>
          ))}
          <Box
            px={3}
            py={2}
            cursor="pointer"
            _hover={{ bg: "bg.error" }}
            fontSize="sm"
            color="finance.negative"
            onClick={() => {
              onLogout();
              setIsOpen(false);
            }}
          >
            <HStack spacing={2}>
              <FiLogOut />
              <Text>Logout</Text>
            </HStack>
          </Box>
        </Box>
      )}
    </Box>
  );
};

const TopNavItem = ({
  label,
  isActive,
  onClick,
}: Omit<NavItemProps, "icon" | "path">) => {
  return (
    <Button
      variant={isActive ? "solid" : "ghost"}
      colorScheme={isActive ? "brand" : "gray"}
      size="sm"
      onClick={onClick}
      fontWeight={isActive ? "semibold" : "medium"}
    >
      {label}
    </Button>
  );
};

interface AccountItemProps {
  account: DedupedAccount;
  onAccountClick: (accountId: string) => void;
  isMultiUser: boolean;
  currentUserId?: string;
  getUserColor: (userId: string) => string;
  getUserBgColor: (userId: string) => string | undefined;
  getUserInitials: (userId: string) => string;
  getUserName: (userId: string) => string;
  isCombinedView: boolean;
  membersLoaded: boolean;
}

const AccountItem = ({
  account,
  onAccountClick,
  isMultiUser,
  currentUserId,
  getUserColor,
  getUserBgColor,
  getUserInitials,
  getUserName,
  isCombinedView,
  membersLoaded,
}: AccountItemProps) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatLastUpdated = (dateStr: string | null) => {
    if (!dateStr) return "Never";

    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const balance = Number(account.current_balance);
  const isNegative = balance < 0;
  const isOwnedByCurrentUser = account.owner_ids.includes(currentUserId || "");

  // Get background color: owner color in multi-user view, subtle grey otherwise
  const primaryOwnerId = account.owner_ids[0];
  const bgColor =
    isCombinedView && isMultiUser
      ? getUserBgColor(primaryOwnerId)
      : "bg.subtle";

  // Check for sync errors
  const hasSyncError = account.last_error_code || account.needs_reauth;
  const errorTooltip = account.needs_reauth
    ? "Reauthentication required - click to reconnect account"
    : account.last_error_message || "Sync error - check account settings";

  return (
    <Box
      px={3}
      py={1.5}
      ml={5}
      bg={bgColor}
      _hover={{ bg: bgColor, opacity: 0.8 }}
      cursor="pointer"
      borderRadius="md"
      transition="all 0.2s"
      onClick={() => onAccountClick(account.id)}
      borderLeftWidth={isOwnedByCurrentUser && isMultiUser ? 3 : 0}
      borderLeftColor="brand.500"
    >
      <VStack align="stretch" spacing={1}>
        <HStack justify="space-between" align="center" spacing={2}>
          <HStack flex={1} minW={0} spacing={1.5}>
            <Text
              fontSize="xs"
              fontWeight="medium"
              color="text.heading"
              noOfLines={1}
              flex={1}
            >
              {account.name}
            </Text>
            {hasSyncError && (
              <Tooltip label={errorTooltip} placement="right" hasArrow>
                <WarningIcon
                  boxSize={3}
                  color={account.needs_reauth ? "orange.500" : "red.500"}
                  flexShrink={0}
                />
              </Tooltip>
            )}
          </HStack>
          <Text
            fontSize="xs"
            fontWeight="semibold"
            color={isNegative ? "finance.negative" : "brand.accent"}
            flexShrink={0}
          >
            {formatCurrency(balance)}
          </Text>
        </HStack>
        <HStack justify="space-between" align="center">
          <Text fontSize="2xs" color="text.muted">
            {formatLastUpdated(account.balance_as_of)}
          </Text>
          {isCombinedView && membersLoaded && isMultiUser && (
            <HStack spacing={1}>
              {account.owner_ids.map((ownerId) => (
                <Tooltip
                  key={ownerId}
                  label={getUserName(ownerId)}
                  placement="top"
                >
                  <Badge
                    size="sm"
                    fontSize="2xs"
                    px={1.5}
                    py={0.5}
                    borderRadius="md"
                    bg={getUserColor(ownerId)}
                    color="white"
                    fontWeight="bold"
                  >
                    {getUserInitials(ownerId)}
                  </Badge>
                </Tooltip>
              ))}
            </HStack>
          )}
        </HStack>
      </VStack>
    </Box>
  );
};

const accountTypeConfig = ACCOUNT_TYPE_SIDEBAR_CONFIG;

const GuestBanner = () => {
  const { isGuest, activeHouseholdName, guestRole, setActiveHousehold } =
    useHouseholdStore(
      useShallow((s) => ({
        isGuest: s.isGuest,
        activeHouseholdName: s.activeHouseholdName,
        guestRole: s.guestRole,
        setActiveHousehold: s.setActiveHousehold,
      })),
    );
  const bannerBg = useColorModeValue("purple.50", "purple.900");
  const bannerBorder = useColorModeValue("purple.200", "purple.700");
  const bannerText = useColorModeValue("purple.800", "purple.100");

  if (!isGuest) return null;

  return (
    <Box
      bg={bannerBg}
      px={4}
      py={2}
      borderBottomWidth={1}
      borderColor={bannerBorder}
    >
      <HStack justify="center" spacing={4}>
        <Text fontSize="sm" color={bannerText} fontWeight="medium">
          Viewing {activeHouseholdName || "guest household"} as guest (
          {guestRole === "viewer" ? "read-only" : "advisor"})
        </Text>
        <Button
          size="xs"
          colorScheme="purple"
          variant="outline"
          onClick={() => setActiveHousehold(null)}
        >
          Return to My Household
        </Button>
      </HStack>
    </Box>
  );
};

export const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isSelfOnlyPage = [
    "/preferences",
    "/permissions",
    "/household",
  ].includes(location.pathname);
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();
  const {
    selectedUserId,
    isCombinedView,
    isOtherUserView,
    canEdit,
    receivedGrants,
    isLoadingGrants,
    selectedMemberIds,
    isAllSelected,
  } = useUserView();
  const logoutMutation = useLogout();
  const {
    isOpen: isAddAccountOpen,
    onOpen: onAddAccountOpen,
    onClose: onAddAccountClose,
  } = useDisclosure();

  // Per-item nav visibility overrides — read-only in Layout; written by PreferencesPage
  const [navOverridesState] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem("nest-egg-nav-visibility");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  // Advanced nav preference — set during onboarding or in Preferences.
  // Uses a storage event listener so the nav updates when the user toggles
  // the preference in PreferencesPage without a full page reload.
  const [showAdvancedNav, setShowAdvancedNav] = useState<boolean>(() => {
    try {
      return localStorage.getItem("nest-egg-show-advanced-nav") === "true";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === "nest-egg-show-advanced-nav") {
        setShowAdvancedNav(e.newValue === "true");
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const [collapsedSections, setCollapsedSections] = useState<
    Record<string, boolean>
  >(() => {
    try {
      const stored = localStorage.getItem("nav-collapsed-sections");
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  // Navigation helper that preserves query params
  const navigateWithParams = (path: string) => {
    const currentUser = searchParams.get("user");
    if (currentUser) {
      navigate(`${path}?user=${currentUser}`);
    } else {
      navigate(path);
    }
  };

  // ── Nav visibility: centralized defaults from useNavDefaults hook ──
  const { accounts, accountsLoading, userAge, conditionalDefaults } =
    useNavDefaults(selectedUserId);

  // Derived flags still needed for feature-discovery toasts
  const has529 = accounts.some((a) => a.account_type === "retirement_529");
  const hasRental = accounts.some((a) => a.is_rental_property);
  const hasLinkedAccounts = accounts.some(
    (a) => a.plaid_item_id !== null || a.plaid_item_hash !== null,
  );
  const hasInvestments = accounts.some((a) =>
    [
      "brokerage",
      "retirement_401k",
      "retirement_ira",
      "retirement_roth_ira",
      "retirement_403b",
      "retirement_457",
      "retirement_pension",
      "crypto",
    ].includes(a.account_type),
  );
  const hasMortgage = accounts.some((a) => a.account_type === "mortgage");
  const hasDebt = accounts.some((a) =>
    ["credit_card", "loan", "student_loan", "mortgage"].includes(a.account_type),
  );
  const isSsAge = userAge !== null && userAge >= 50;

  // Helper: check if a nav item is visible
  // Priority: per-item override (navOverridesState) > account-based default
  const isNavVisible = (path: string): boolean => {
    if (accountsLoading) return true; // show while loading to avoid flicker
    // Explicit user override always wins — they may manually enable items
    // before adding relevant accounts (e.g. Rental Properties before adding
    // a rental, SS Optimizer to preview the tool).
    if (path in navOverridesState) return navOverridesState[path];
    // No override — use account/age-based conditional default
    return conditionalDefaults[path] ?? true;
  };

  // Feature discovery: toast once when conditional nav items first unlock
  // useNotificationToast bridges these into the bell dropdown as well
  const notificationToast = useNotificationToast();

  // First-login view orientation — fires once on the very first session
  useEffect(() => {
    if (!user) return;
    if ((user.login_count ?? 0) !== 1) return;
    const FIRST_LOGIN_KEY = "nest-egg-first-login-view-shown";
    if (localStorage.getItem(FIRST_LOGIN_KEY)) return;
    localStorage.setItem(FIRST_LOGIN_KEY, "true");
    const viewLabel = isCombinedView
      ? "Combined (all household members)"
      : isOtherUserView
        ? "another member's view"
        : "your personal view";
    notificationToast({
      duration: 10000,
      isClosable: true,
      position: "bottom-right",
      render: ({ onClose }) => (
        <Box bg="purple.600" color="white" px={4} py={3} borderRadius="md" boxShadow="lg">
          <HStack justify="space-between" align="start" spacing={3}>
            <Box flex={1}>
              <Text fontWeight="semibold" fontSize="sm">Welcome to Nest Egg!</Text>
              <Text fontSize="xs" mt={0.5} opacity={0.9}>
                You're viewing data in <strong>{viewLabel}</strong>. Change this anytime from the view switcher in the top bar, or customize which tabs appear in Preferences → Display.
              </Text>
            </Box>
            <HStack spacing={2} flexShrink={0}>
              <Button
                size="xs"
                colorScheme="whiteAlpha"
                variant="solid"
                onClick={() => { navigate("/preferences"); onClose(); }}
              >
                Preferences →
              </Button>
              <Button
                size="xs"
                variant="ghost"
                color="white"
                _hover={{ bg: "whiteAlpha.200" }}
                onClick={onClose}
              >
                ✕
              </Button>
            </HStack>
          </HStack>
        </Box>
      ),
    });
  }, [user, isCombinedView, isOtherUserView, notificationToast]);

  useEffect(() => {
    if (accountsLoading) return;
    const DISCOVERY_KEY = "nest-egg-feature-discovery-shown";
    let shown: Record<string, boolean> = {};
    try {
      shown = JSON.parse(localStorage.getItem(DISCOVERY_KEY) || "{}");
    } catch {
      /* ignore */
    }

    const announce = (key: string, title: string, description: string, path: string) => {
      if (!shown[key]) {
        shown[key] = true;
        localStorage.setItem(DISCOVERY_KEY, JSON.stringify(shown));
        notificationToast({
          duration: 8000,
          isClosable: true,
          position: "bottom-right",
          render: ({ onClose }) => (
            <Box
              bg="blue.600"
              color="white"
              px={4}
              py={3}
              borderRadius="md"
              boxShadow="lg"
            >
              <HStack justify="space-between" align="start" spacing={3}>
                <Box flex={1}>
                  <Text fontWeight="semibold" fontSize="sm">{title}</Text>
                  <Text fontSize="xs" mt={0.5} opacity={0.9}>{description}</Text>
                </Box>
                <HStack spacing={2} flexShrink={0}>
                  <Button
                    size="xs"
                    colorScheme="whiteAlpha"
                    variant="solid"
                    onClick={() => { navigate(path); onClose(); }}
                  >
                    Go →
                  </Button>
                  <Button
                    size="xs"
                    variant="ghost"
                    color="white"
                    _hover={{ bg: "whiteAlpha.200" }}
                    onClick={onClose}
                  >
                    ✕
                  </Button>
                </HStack>
              </HStack>
            </Box>
          ),
          notification: {
            type: NotificationType.NAV_FEATURE_UNLOCKED,
            priority: NotificationPriority.MEDIUM,
            title,
            message: description,
            action_url: path,
            action_label: "Explore",
            expires_in_days: 30,
          },
        });
      }
    };

    if (has529) {
      announce(
        "education",
        "Education Planning unlocked",
        "You added a 529 account — visit Education Planning under Planning to project college costs.",
        "/education",
      );
    }
    if (hasRental) {
      announce(
        "rental-properties",
        "Rental Properties unlocked",
        "You added a rental property — Rental Properties is now in your Analytics menu for income tracking.",
        "/rental-properties",
      );
    }
    if (hasLinkedAccounts) {
      announce(
        "linked-accounts",
        "Recurring & Bills unlocked",
        "Your bank is connected — Recurring and Bills are now visible under Spending.",
        "/recurring",
      );
    }
    if (hasInvestments) {
      announce(
        "investments-nav",
        "Investment features unlocked",
        "With investment accounts you now have access to Tax Deductible under Analytics, and fund fee/expense ratio analysis on the Investments page.",
        "/tax-deductible",
      );
    }
    if (hasMortgage) {
      announce(
        "mortgage-nav",
        "Mortgage Planner unlocked",
        "You have a mortgage — Mortgage is now in your Planning menu for amortization and refinance analysis.",
        "/mortgage",
      );
    }
    if (hasDebt) {
      announce(
        "debt-payoff-nav",
        "Debt Payoff unlocked",
        "You have loans or credit card debt — Debt Payoff is now in Planning to model your fastest payoff strategy.",
        "/debt-payoff",
      );
    }
    if (isSsAge) {
      announce(
        "ss-optimizer-nav",
        "SS Optimizer unlocked",
        "Based on your age, Social Security planning is now available under Planning — find the best age to claim.",
        "/ss-claiming",
      );
    }
    // Nudge users who have accounts but haven't turned on advanced features
    if (!showAdvancedNav && (has529 || hasRental || hasInvestments || hasLinkedAccounts)) {
      announce(
        "advanced-nav-hint",
        "Advanced features available",
        "FIRE planning, Tax Projection, and more are hidden by default. Enable them in Preferences → Display.",
        "/preferences",
      );
    }
  }, [
    has529,
    hasRental,
    hasLinkedAccounts,
    hasInvestments,
    hasMortgage,
    hasDebt,
    isSsAge,
    showAdvancedNav,
    accountsLoading,
    notificationToast,
  ]);

  // All nav items with default visibility
  const allSpendingItems = [
    {
      label: "Transactions",
      path: "/transactions",
      tooltip:
        "Every purchase, payment, and deposit — search and filter your full history",
    },
    {
      label: "Budgets",
      path: "/budgets",
      tooltip:
        "Set monthly or custom spending limits by category and get alerts when you're close",
    },
    {
      label: "Recurring & Bills",
      path: "/recurring-bills",
      tooltip:
        "Subscriptions, recurring payments, and upcoming bill due dates — all in one place",
    },
    {
      label: "Categories & Labels",
      path: "/categories",
      tooltip:
        "Organize transactions into groups (Groceries, Dining, etc.) to understand your spending",
    },
    {
      label: "Rules",
      path: "/rules",
      tooltip:
        "Auto-categorize transactions — e.g. anything from 'Starbucks' goes to Dining",
    },
  ];

  const allAnalyticsItems = [
    {
      label: "Cash Flow",
      path: "/income-expenses",
      tooltip:
        "Visual breakdown of income vs. spending — see where your money comes from and goes",
    },
    {
      label: "Cash Flow Forecast",
      path: "/cash-flow-forecast",
      tooltip:
        "30/60/90-day projected balance with upcoming transactions and low-balance alerts",
    },
    {
      label: "Net Worth Timeline",
      path: "/net-worth-timeline",
      tooltip:
        "Chart of your total assets minus debts over time — the single most important financial number",
    },
    {
      label: "Trends",
      path: "/trends",
      tooltip:
        "Month-over-month spending patterns by category — spot habits and changes over time",
    },
    {
      label: "Reports",
      path: "/reports",
      tooltip:
        "Custom reports: filter by date, account, or category and export to CSV",
    },
    {
      label: "Year in Review",
      path: "/year-in-review",
      tooltip:
        "Annual financial summary — biggest expenses, income milestones, and net worth growth",
    },
    {
      label: "Smart Insights",
      path: "/smart-insights",
      tooltip: "Personalized tips based on your actual data — savings opportunities, fee alerts, and more",
    },
    {
      label: "Financial Health",
      path: "/financial-health",
      tooltip: "Financial ratios, debt-to-income, emergency fund coverage, and liquidity analysis",
    },
    {
      label: "Tax Deductible",
      path: "/tax-deductible",
      tooltip:
        "Transactions flagged as tax-deductible — helpful for filing or working with an accountant",
    },
    {
      label: "Rental Properties",
      path: "/rental-properties",
      tooltip:
        "Track rental income and expenses, and see your net operating income per property",
    },
  ];

  const allPlanningItems = [
    // ── Front and center ──────────────────────────────────────────────────
    {
      label: "Financial Plan",
      path: "/financial-plan",
      tooltip:
        "Unified financial health view — retirement, education, debt, insurance, estate, and emergency fund at a glance",
    },
    {
      label: "Goals",
      path: "/goals",
      tooltip:
        "Set savings targets (emergency fund, vacation, down payment) and track your progress",
    },
    // ── Core planning ─────────────────────────────────────────────────────
    {
      label: "Retirement",
      path: "/retirement",
      tooltip:
        "Project whether you'll have enough to retire — see your savings trajectory and model different life scenarios",
    },
    {
      label: "Education",
      path: "/education",
      tooltip:
        "529 college savings projections — see if you're on track to cover tuition costs per child",
    },
    {
      label: "Debt Payoff",
      path: "/debt-payoff",
      tooltip:
        "Pick a payoff strategy — pay smallest debts first for quick wins, or highest interest first to save money — and see exactly when you'll be debt-free",
    },
    {
      label: "Mortgage",
      path: "/mortgage",
      tooltip:
        "Analyze your mortgage: amortization schedule, extra payment impact, and break-even on refinancing",
    },
    // ── Consolidated hubs ─────────────────────────────────────────────────
    // Note: HSA Planner is inside Investment Tools — no separate nav entry needed
    {
      label: "Tax Center",
      path: "/tax-center",
      tooltip:
        "Tax projection, three-bucket optimization, charitable giving, IRMAA, Roth wizard, and contribution headroom",
    },
    {
      label: "Life Planning",
      path: "/life-planning",
      tooltip:
        "Social Security optimizer, variable income smoothing, estate & beneficiary planning, RMD projections, insurance audit, and pension modeling — per-person tools for households",
    },
    {
      label: "Planning Tools",
      path: "/investment-tools",
      tooltip:
        "FIRE metrics, equity compensation, loan modeler, HSA optimizer, tax-equivalent yield, asset location, employer match, and cost basis aging",
      advanced: true,
    },
    {
      label: "What-If Scenarios",
      path: "/what-if",
      tooltip:
        "Mortgage vs invest, salary change, relocation tax impact, early retirement analysis",
    },
    {
      label: "Bond Ladder",
      path: "/bond-ladder",
      tooltip: "Build a Treasury/CD/TIPS bond ladder for income generation",
      advanced: true,
    },
    {
      label: "PE Performance",
      path: "/pe-performance",
      tooltip: "Private equity TVPI, DPI, RVPI, IRR metrics and capital call history",
      advanced: true,
    },
  ];

  const filterVisible = (
    items: {
      label: string;
      path: string;
      tooltip?: string;
      advanced?: boolean;
    }[],
  ): { label: string; path: string; tooltip?: string }[] =>
    items.filter((item) => {
      if (!isNavVisible(item.path)) return false;
      // Advanced items are hidden by default unless:
      // (a) the master advanced-nav switch is on, OR
      // (b) the user has an explicit per-item override enabling it
      if (item.advanced && !showAdvancedNav && !(item.path in navOverridesState && navOverridesState[item.path])) {
        return false;
      }
      return true;
    });

  const spendingMenuItems = filterVisible(allSpendingItems);
  const analyticsMenuItems = filterVisible(allAnalyticsItems);
  const planningMenuItems = filterVisible(allPlanningItems);

  // Fetch dashboard summary for net worth (filtered by user)
  const { data: dashboardSummary } = useQuery({
    queryKey: ["dashboard-summary", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get("/dashboard/summary", { params });
      return response.data;
    },
  });

  // Fetch household members for color coding
  const { data: members } = useHouseholdMembers();

  // Assign colors to users for visual distinction in combined view
  const userColors = [
    "blue.500",
    "green.500",
    "purple.500",
    "orange.500",
    "pink.500",
  ];
  const userBgColors = useColorModeValue(
    ["blue.50", "green.50", "purple.50", "orange.50", "pink.50"],
    ["blue.900", "green.900", "purple.900", "orange.900", "pink.900"],
  );
  const householdBannerBg = useColorModeValue("teal.50", "teal.900");

  const getUserColorIndex = (userId: string): number => {
    if (!members) return 0;
    const memberIndex = members.findIndex((m) => m.id === userId);
    return memberIndex >= 0 ? memberIndex : 0;
  };

  const getUserColor = (userId: string): string => {
    const index = getUserColorIndex(userId);
    return userColors[index % userColors.length];
  };

  const getUserBgColor = (userId: string): string | undefined => {
    if (!isCombinedView) return undefined;
    const index = getUserColorIndex(userId);
    return userBgColors[index % userBgColors.length];
  };

  const getUserName = (userId: string): string => {
    if (!members || !userId) {
      return "";
    }

    const member = members.find((m) => m.id === userId);
    if (!member) {
      return "";
    }

    // Try display_name first
    if (member.display_name && member.display_name.trim()) {
      return member.display_name.trim();
    }

    // Try first_name + last_name
    if (member.first_name && member.first_name.trim()) {
      if (member.last_name && member.last_name.trim()) {
        return `${member.first_name.trim()} ${member.last_name.trim()}`;
      }
      return member.first_name.trim();
    }

    // Fallback to email username
    if (member.email && member.email.includes("@")) {
      return member.email.split("@")[0];
    }

    return "";
  };

  const getUserInitials = (userId: string): string => {
    const name = getUserName(userId);
    if (!name || name.length === 0) return "?";

    // Split by space to get first and last name
    const parts = name.split(" ").filter((p) => p.length > 0);

    if (parts.length >= 2) {
      // Use first letter of first word and first letter of last word
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    // Single word name - use first two characters
    if (name.length >= 2) {
      return name.substring(0, 2).toUpperCase();
    }

    // Very short name - use first character twice
    return (name[0] + name[0]).toUpperCase();
  };

  // Deduplicate accounts in combined view
  const dedupedAccounts: DedupedAccount[] =
    isCombinedView && accounts
      ? (() => {
          const hashMap = new Map<string, DedupedAccount>();

          accounts.forEach((account) => {
            const hash = account.plaid_item_hash || account.id; // Use account ID if no hash

            if (hashMap.has(hash)) {
              // Account already exists, add this user as an owner
              const existing = hashMap.get(hash)!;
              if (!existing.owner_ids.includes(account.user_id)) {
                existing.owner_ids.push(account.user_id);
                existing.is_shared = true;
              }
            } else {
              // First time seeing this account
              hashMap.set(hash, {
                ...account,
                owner_ids: [account.user_id],
                is_shared: false,
              });
            }
          });

          return Array.from(hashMap.values());
        })()
      : accounts?.map((account) => ({
          ...account,
          owner_ids: [account.user_id],
          is_shared: false,
        })) || [];

  // Group accounts by type (using deduplicated accounts)
  const groupedAccounts = dedupedAccounts?.reduce(
    (acc, account) => {
      const typeConfig = accountTypeConfig[account.account_type] || {
        label: "Other",
        order: 7,
      };
      const label = typeConfig.label;

      if (!acc[label]) {
        acc[label] = [];
      }
      acc[label].push(account);
      return acc;
    },
    {} as Record<string, DedupedAccount[]>,
  );

  // Sort groups by order
  const sortedGroups = groupedAccounts
    ? Object.entries(groupedAccounts).sort((a, b) => {
        const aOrder =
          accountTypeConfig[
            accounts?.find(
              (acc) => accountTypeConfig[acc.account_type]?.label === a[0],
            )?.account_type || ""
          ]?.order || 7;
        const bOrder =
          accountTypeConfig[
            accounts?.find(
              (acc) => accountTypeConfig[acc.account_type]?.label === b[0],
            )?.account_type || ""
          ]?.order || 7;
        return aOrder - bOrder;
      })
    : [];

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  const handleAccountClick = (accountId: string) => {
    navigateWithParams(`/accounts/${accountId}`);
  };

  const toggleSection = (sectionName: string) => {
    setCollapsedSections((prev) => {
      const next = { ...prev, [sectionName]: !prev[sectionName] };
      try {
        localStorage.setItem("nav-collapsed-sections", JSON.stringify(next));
      } catch {
        /* localStorage unavailable — ignore */
      }
      return next;
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatLastUpdated = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  // Redirect new users who haven't completed onboarding
  if (user && !user.onboarding_completed) {
    return <Navigate to="/welcome" replace />;
  }

  return (
    <Flex h="100vh" flexDirection="column" overflow="hidden">
      {/* Offline indicator — shown when network connectivity is lost */}
      <OfflineIndicator />

      {/* Email verification banner — shown when user's email is not yet verified */}
      <EmailVerificationBanner />

      {/* Milestone celebration overlay — confetti on $100K, $500K, $1M etc. */}
      <MilestoneCelebration />

      {/* Guest household banner */}
      <GuestBanner />

      {/* Top Header */}
      <Box
        bg="bg.surface"
        borderBottomWidth={1}
        borderColor="border.default"
        px={6}
        py={3}
        position="sticky"
        top={0}
        zIndex={10}
      >
        <HStack justify="space-between">
          {/* Left: Logo + Navigation */}
          <HStack spacing={8}>
            <Text
              fontSize="xl"
              fontWeight="bold"
              color="brand.accent"
              whiteSpace="nowrap"
            >
              Nest Egg
            </Text>
            <HStack spacing={1} ml={36}>
              {/* Overview */}
              <TopNavItem
                label="Overview"
                isActive={location.pathname === "/overview"}
                onClick={() => navigateWithParams("/overview")}
              />

              {/* Calendar */}
              <TopNavItem
                label="Calendar"
                isActive={location.pathname === "/calendar"}
                onClick={() => navigateWithParams("/calendar")}
              />

              {/* Spending Dropdown */}
              <NavDropdown
                label="Spending"
                items={spendingMenuItems}
                currentPath={location.pathname}
                onNavigate={navigateWithParams}
              />

              {/* Analytics Dropdown */}
              <NavDropdown
                label="Analytics"
                items={analyticsMenuItems}
                currentPath={location.pathname}
                onNavigate={navigateWithParams}
              />

              {/* Planning Dropdown */}
              <NavDropdown
                label="Planning"
                items={planningMenuItems}
                currentPath={location.pathname}
                onNavigate={navigateWithParams}
              />


              {/* Portfolio */}
              <TopNavItem
                label="Portfolio"
                isActive={location.pathname === "/investments"}
                onClick={() => navigateWithParams("/investments")}
              />

              {/* Accounts */}
              <TopNavItem
                label="Accounts"
                isActive={location.pathname === "/accounts"}
                onClick={() => navigateWithParams("/accounts")}
              />
            </HStack>
          </HStack>

          {/* Right: Household Switcher, User View Toggle, Notification Bell and User Menu */}
          <HStack spacing={4}>
            <HouseholdSwitcher />
            <Box ml={10}>
              <UserViewToggle />
            </Box>
            <NotificationBell />

            <UserMenu
              user={
                user as {
                  first_name?: string;
                  last_name?: string;
                  display_name?: string;
                  email?: string;
                } | null
              }
              onNavigate={navigateWithParams}
              onLogout={handleLogout}
              isMultiMemberHousehold={(members?.length ?? 0) >= 2}
            />
          </HStack>
        </HStack>
      </Box>

      {/* View Indicator Banner */}
      {!isCombinedView &&
        members &&
        members.length > 1 &&
        (() => {
          if (!isOtherUserView || isSelfOnlyPage) {
            // Own-view banner (blue) — also shown on self-only pages regardless of selected view
            return (
              <Box
                bg="bg.info"
                borderBottomWidth={1}
                borderColor="border.default"
                px={8}
                py={2}
              >
                <HStack spacing={3}>
                  <Text
                    fontSize="sm"
                    fontWeight="semibold"
                    color="text.primary"
                  >
                    📊 Your View:
                  </Text>
                  <Badge
                    size="sm"
                    fontSize="xs"
                    px={2}
                    py={1}
                    borderRadius="md"
                    bg={getUserColor(user?.id || "")}
                    color="white"
                    fontWeight="bold"
                  >
                    {getUserInitials(user?.id || "")}
                  </Badge>
                  <Text fontSize="sm" fontWeight="medium" color="text.heading">
                    {getUserName(user?.id || "")}'s Accounts
                  </Text>
                </HStack>
              </Box>
            );
          }

          // Other-user banner: check page-specific access
          if (isLoadingGrants) {
            return (
              <Box
                bg="bg.subtle"
                borderBottomWidth={1}
                borderColor="border.default"
                px={8}
                py={2}
              >
                <HStack spacing={3}>
                  <Spinner size="xs" color="text.muted" />
                  <Text fontSize="sm" color="text.muted">
                    Loading permissions…
                  </Text>
                </HStack>
              </Box>
            );
          }

          const pageResourceType = getResourceTypeForPath(location.pathname);
          const access = getBannerAccess(
            receivedGrants,
            selectedUserId ?? "",
            pageResourceType,
          );
          const sectionLabel = pageResourceType
            ? (RESOURCE_TYPE_LABELS[pageResourceType] ?? pageResourceType)
            : "Data";
          const viewedName = getUserName(selectedUserId ?? "");

          // Household members always have at least read access — 'none' (no explicit grant)
          // still means read-only, not blocked.
          const canWrite = access === "write";
          const bannerConfig = canWrite
            ? {
                bg: "bg.success",
                border: "border.default",
                headColor: "text.primary",
                textColor: "text.heading",
                icon: "✏️",
                prefix: "Can Edit:",
                suffix: `'s ${sectionLabel}`,
              }
            : {
                bg: "bg.info",
                border: "border.default",
                headColor: "text.primary",
                textColor: "text.heading",
                icon: "👁️",
                prefix: "Read Only:",
                suffix: `'s ${sectionLabel}`,
              };

          return (
            <Box
              bg={bannerConfig.bg}
              borderBottomWidth={1}
              borderColor={bannerConfig.border}
              px={8}
              py={2}
            >
              <HStack spacing={3}>
                <Text
                  fontSize="sm"
                  fontWeight="semibold"
                  color={bannerConfig.headColor}
                >
                  {bannerConfig.icon} {bannerConfig.prefix}
                </Text>
                <Badge
                  size="sm"
                  fontSize="xs"
                  px={2}
                  py={1}
                  borderRadius="md"
                  bg={getUserColor(selectedUserId ?? "")}
                  color="white"
                  fontWeight="bold"
                >
                  {getUserInitials(selectedUserId ?? "")}
                </Badge>
                <Text
                  fontSize="sm"
                  fontWeight="medium"
                  color={bannerConfig.textColor}
                >
                  {viewedName}
                  {bannerConfig.suffix}
                </Text>
              </HStack>
            </Box>
          );
        })()}

      {/* Multi-member permission banner — shown in combined view when other members are selected */}
      {isCombinedView &&
        members &&
        members.length > 1 &&
        !isSelfOnlyPage &&
        (() => {
          const pageResourceType = getResourceTypeForPath(location.pathname);
          const sectionLabel = pageResourceType
            ? (RESOURCE_TYPE_LABELS[pageResourceType] ?? pageResourceType)
            : "Data";
          const memberAccess = getMultiMemberAccess(
            receivedGrants,
            user?.id ?? "",
            selectedMemberIds,
            pageResourceType,
          );

          // Nothing to show if only self is selected
          if (memberAccess.length === 0) return null;

          // Still loading grants
          if (isLoadingGrants) {
            return (
              <Box
                bg="bg.info"
                borderBottomWidth={1}
                borderColor="border.default"
                px={8}
                py={2}
              >
                <HStack spacing={3}>
                  <Spinner size="xs" color="text.muted" />
                  <Text fontSize="sm" color="text.muted">
                    Loading permissions…
                  </Text>
                </HStack>
              </Box>
            );
          }

          // Distinct banner colors:
          //   All members selected → teal (pleasant in both light & dark)
          //   Partial selection    → green (bg.success) — distinct from self-view's blue
          const bannerBg = isAllSelected ? householdBannerBg : "bg.success";

          return (
            <Box
              bg={bannerBg}
              borderBottomWidth={1}
              borderColor="border.default"
              px={8}
              py={2}
            >
              <HStack spacing={3}>
                <Text fontSize="sm" fontWeight="semibold" color="text.primary">
                  {isAllSelected
                    ? `🏠 Household View — ${sectionLabel} Permissions:`
                    : `👥 ${sectionLabel} Permissions:`}
                </Text>
                <HStack spacing={2} flexWrap="wrap">
                  {memberAccess.map(({ memberId, access }) => {
                    const canWrite = access === "write";
                    return (
                      <HStack
                        key={memberId}
                        spacing={2}
                        px={2.5}
                        py={0.5}
                        borderWidth={1}
                        borderColor="border.default"
                        borderRadius="md"
                        bg="bg.surface"
                      >
                        <Badge
                          size="sm"
                          fontSize="xs"
                          px={1.5}
                          py={0.5}
                          borderRadius="md"
                          bg={getUserColor(memberId)}
                          color="white"
                          fontWeight="bold"
                        >
                          {getUserInitials(memberId)}
                        </Badge>
                        <Text
                          fontSize="sm"
                          color="text.heading"
                          fontWeight="medium"
                        >
                          {getUserName(memberId)}
                        </Text>
                        <Badge
                          fontSize="2xs"
                          px={1.5}
                          py={0}
                          borderRadius="full"
                          colorScheme={canWrite ? "green" : "blue"}
                          variant="subtle"
                          lineHeight="tall"
                        >
                          {canWrite ? "✏️ Edit" : "👁️ Read"}
                        </Badge>
                      </HStack>
                    );
                  })}
                </HStack>
              </HStack>
            </Box>
          );
        })()}

      <Flex flex={1} overflow="hidden">
        {/* Left Sidebar - Accounts */}
        <Box
          w="280px"
          bg="bg.surface"
          borderRightWidth={1}
          borderColor="border.default"
          overflowY="auto"
          p={3}
        >
          <VStack align="stretch" spacing={2} mb={3}>
            <HStack justify="space-between">
              <VStack align="start" spacing={0}>
                <Text
                  fontSize="sm"
                  fontWeight="bold"
                  textTransform="uppercase"
                  color="text.heading"
                  letterSpacing="wide"
                >
                  Accounts
                </Text>
                {!isCombinedView && members && members.length > 1 && (
                  <HStack spacing={1} mt={1}>
                    <Badge
                      size="sm"
                      fontSize="2xs"
                      px={1.5}
                      py={0.5}
                      borderRadius="md"
                      bg={getUserColor(selectedUserId || user?.id || "")}
                      color="white"
                      fontWeight="bold"
                    >
                      {getUserInitials(selectedUserId || user?.id || "")}
                    </Badge>
                    <Text fontSize="2xs" color="text.secondary">
                      {getUserName(selectedUserId || user?.id || "")}
                    </Text>
                  </HStack>
                )}
              </VStack>
              {dashboardSummary?.net_worth !== undefined && (
                <VStack align="end" spacing={0}>
                  <Text
                    fontSize="md"
                    fontWeight="bold"
                    color={
                      dashboardSummary.net_worth >= 0
                        ? "finance.positive"
                        : "finance.negative"
                    }
                  >
                    {formatCurrency(Number(dashboardSummary.net_worth))}
                  </Text>
                  {(() => {
                    // Show oldest sync time across linked accounts so users know
                    // when the stalest balance was last refreshed
                    const synced = (accounts ?? [])
                      .map((a) => a.last_synced_at)
                      .filter(Boolean) as string[];
                    if (synced.length === 0) return null;
                    const oldest = synced.sort()[0];
                    return (
                      <Text fontSize="2xs" color="text.muted">
                        as of {formatLastUpdated(oldest)}
                      </Text>
                    );
                  })()}
                </VStack>
              )}
            </HStack>
          </VStack>

          {/* User color legend in combined view */}
          {isCombinedView && members && members.length > 1 && (
            <Box mb={3} p={2} bg="bg.subtle" borderRadius="md">
              <Text
                fontSize="2xs"
                fontWeight="semibold"
                color="text.secondary"
                mb={1.5}
              >
                HOUSEHOLD MEMBERS
              </Text>
              <VStack spacing={1} align="stretch">
                {members.map((member, index) => (
                  <HStack key={member.id} spacing={2}>
                    <Badge
                      size="sm"
                      fontSize="2xs"
                      px={1.5}
                      py={0.5}
                      borderRadius="md"
                      bg={userColors[index % userColors.length]}
                      color="white"
                      fontWeight="bold"
                    >
                      {getUserInitials(member.id)}
                    </Badge>
                    <Text fontSize="2xs" color="text.heading">
                      {getUserName(member.id)}
                    </Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          )}

          {accountsLoading ? (
            <Center py={8}>
              <Spinner size="sm" color="brand.500" />
            </Center>
          ) : (
            <VStack spacing={2} align="stretch">
              {sortedGroups.map(([groupName, groupAccounts]) => {
                const groupTotal = groupAccounts.reduce(
                  (sum, account) => sum + Number(account.current_balance),
                  0,
                );
                const isCollapsed = collapsedSections[groupName];

                return (
                  <Box key={groupName}>
                    <HStack
                      justify="space-between"
                      mb={1}
                      px={2}
                      py={1.5}
                      cursor="pointer"
                      _hover={{ bg: "bg.subtle" }}
                      borderRadius="md"
                      onClick={() => toggleSection(groupName)}
                    >
                      <HStack spacing={2}>
                        {isCollapsed ? (
                          <ChevronRightIcon
                            boxSize={3.5}
                            color="text.secondary"
                          />
                        ) : (
                          <ChevronDownIcon
                            boxSize={3.5}
                            color="text.secondary"
                          />
                        )}
                        <Text
                          fontSize="sm"
                          fontWeight="bold"
                          color="text.heading"
                          textTransform="uppercase"
                          letterSpacing="wide"
                        >
                          {groupName}
                        </Text>
                      </HStack>
                      <Text
                        fontSize="sm"
                        fontWeight="bold"
                        color={
                          groupTotal < 0 ? "finance.negative" : "text.primary"
                        }
                      >
                        {formatCurrency(groupTotal)}
                      </Text>
                    </HStack>
                    <Collapse in={!isCollapsed} animateOpacity>
                      <VStack spacing={0.5} align="stretch" mb={2}>
                        {groupAccounts.map((account) => (
                          <AccountItem
                            key={account.id}
                            account={account}
                            isMultiUser={!!members && members.length > 1}
                            onAccountClick={handleAccountClick}
                            currentUserId={user?.id}
                            getUserColor={getUserColor}
                            getUserBgColor={getUserBgColor}
                            getUserInitials={getUserInitials}
                            getUserName={getUserName}
                            isCombinedView={isCombinedView}
                            membersLoaded={!!members}
                          />
                        ))}
                      </VStack>
                    </Collapse>
                  </Box>
                );
              })}

              {(!sortedGroups || sortedGroups.length === 0) && (
                <Text
                  fontSize="sm"
                  color="text.muted"
                  textAlign="center"
                  py={8}
                >
                  {isOtherUserView
                    ? "This user has no accounts yet."
                    : "No accounts yet. Connect an account to get started."}
                </Text>
              )}

              {!isOtherUserView && (
                <Tooltip
                  label={
                    !canEdit
                      ? "You can only add accounts for yourself or in combined view"
                      : ""
                  }
                  placement="top"
                  isDisabled={canEdit}
                >
                  <Button
                    leftIcon={<AddIcon />}
                    colorScheme="brand"
                    size="sm"
                    onClick={onAddAccountOpen}
                    mt={2}
                    w="full"
                    isDisabled={!canEdit}
                  >
                    Add Account
                  </Button>
                </Tooltip>
              )}
            </VStack>
          )}
        </Box>

        {/* Main content area */}
        <Box flex={1} overflowY="auto" bg="bg.canvas" pl={8}>
          <RouteErrorBoundary>
            <Outlet />
          </RouteErrorBoundary>
        </Box>
      </Flex>

      {/* Add Account Modal */}
      <AddAccountModal isOpen={isAddAccountOpen} onClose={onAddAccountClose} />
    </Flex>
  );
};
