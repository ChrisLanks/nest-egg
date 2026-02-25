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
import { UserViewToggle } from "./UserViewToggle";
import { useUserView } from "../contexts/UserViewContext";
import { EmailVerificationBanner } from "./EmailVerificationBanner";
import {
  RESOURCE_TYPE_LABELS,
  getBannerAccess,
  getResourceTypeForPath,
} from "../utils/permissionBannerUtils";
import { ACCOUNT_TYPE_SIDEBAR_CONFIG } from "../constants/accountTypeGroups";

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
  items: { label: string; path: string }[];
  currentPath: string;
  onNavigate: (path: string) => void;
}

const NavDropdown = ({ label, items, currentPath, onNavigate }: NavDropdownProps) => {
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
            <Box
              key={item.path}
              px={3}
              py={2}
              cursor="pointer"
              fontWeight={currentPath === item.path ? "semibold" : "normal"}
              bg={currentPath === item.path ? "brand.subtle" : "transparent"}
              _hover={{ bg: currentPath === item.path ? "brand.subtle" : "bg.subtle" }}
              fontSize="sm"
              onClick={() => {
                onNavigate(item.path);
                setIsOpen(false);
              }}
            >
              {item.label}
            </Box>
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
}: {
  user: { first_name?: string; last_name?: string; display_name?: string; email?: string } | null;
  onNavigate: (path: string) => void;
  onLogout: () => void;
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
    { label: "Permissions", icon: <FiSettings />, path: "/permissions" },
    { label: "Preferences", icon: <FiSettings />, path: "/preferences" },
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
            name={user?.display_name || `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.email}
            bg="brand.500"
          />
          <VStack align="start" spacing={0}>
            <Text fontSize="sm" fontWeight="medium">
              {user?.display_name || `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim() || user?.email}
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
  const bgColor = isCombinedView && isMultiUser ? getUserBgColor(primaryOwnerId) : "bg.subtle";

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


export const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isSelfOnlyPage = ['/preferences', '/permissions', '/household'].includes(location.pathname);
  const [searchParams] = useSearchParams();
  const { user } = useAuthStore();
  const { selectedUserId, isCombinedView, isOtherUserView, canEdit, receivedGrants, isLoadingGrants } =
    useUserView();
  const logoutMutation = useLogout();
  const {
    isOpen: isAddAccountOpen,
    onOpen: onAddAccountOpen,
    onClose: onAddAccountClose,
  } = useDisclosure();

  const [collapsedSections, setCollapsedSections] = useState<
    Record<string, boolean>
  >(() => {
    try {
      const stored = localStorage.getItem('nav-collapsed-sections');
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

  const planningMenuItems = [
    { label: "Budgets", path: "/budgets" },
    { label: "Goals", path: "/goals" },
    { label: "Retirement", path: "/retirement" },
    { label: "Debt Payoff", path: "/debt-payoff" },
  ];

  const analyticsMenuItems = [
    { label: "Cash Flow", path: "/income-expenses" },
    { label: "Trends", path: "/trends" },
    { label: "Reports", path: "/reports" },
    { label: "Tax Deductible", path: "/tax-deductible" },
  ];

  const transactionsMenuItems = [
    { label: "Transactions", path: "/transactions" },
    { label: "Categories", path: "/categories" },
    { label: "Rules", path: "/rules" },
    { label: "Recurring", path: "/recurring" },
    { label: "Bills", path: "/bills" },
  ];

  // Fetch accounts with user filtering
  const { data: accounts, isLoading: accountsLoading } = useQuery<Account[]>({
    queryKey: ["accounts", selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get("/accounts", { params });
      return response.data;
    },
  });

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
        localStorage.setItem('nav-collapsed-sections', JSON.stringify(next));
      } catch { /* localStorage unavailable — ignore */ }
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

  return (
    <Flex h="100vh" flexDirection="column" overflow="hidden">
      {/* Email verification banner — shown when user's email is not yet verified */}
      <EmailVerificationBanner />

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

              {/* Planning & Goals Dropdown */}
              <NavDropdown
                label="Planning & Goals"
                items={planningMenuItems}
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

              {/* Transactions Dropdown */}
              <NavDropdown
                label="Transactions"
                items={transactionsMenuItems}
                currentPath={location.pathname}
                onNavigate={navigateWithParams}
              />

              {/* Investments */}
              <TopNavItem
                label="Investments"
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

          {/* Right: User View Toggle, Notification Bell and User Menu */}
          <HStack spacing={4}>
            <Box ml={10}>
              <UserViewToggle />
            </Box>
            <NotificationBell />

            <UserMenu
              user={user as { first_name?: string; last_name?: string; display_name?: string; email?: string } | null}
              onNavigate={navigateWithParams}
              onLogout={handleLogout}
            />
          </HStack>
        </HStack>
      </Box>

      {/* View Indicator Banner */}
      {!isCombinedView && members && members.length > 1 && (() => {
        if (!isOtherUserView || isSelfOnlyPage) {
          // Own-view banner (blue) — also shown on self-only pages regardless of selected view
          return (
            <Box bg="bg.info" borderBottomWidth={1} borderColor="border.default" px={8} py={2}>
              <HStack spacing={3}>
                <Text fontSize="sm" fontWeight="semibold" color="text.primary">📊 Your View:</Text>
                <Badge size="sm" fontSize="xs" px={2} py={1} borderRadius="md"
                  bg={getUserColor(user?.id || "")} color="white" fontWeight="bold">
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
            <Box bg="bg.subtle" borderBottomWidth={1} borderColor="border.default" px={8} py={2}>
              <HStack spacing={3}>
                <Spinner size="xs" color="text.muted" />
                <Text fontSize="sm" color="text.muted">Loading permissions…</Text>
              </HStack>
            </Box>
          );
        }

        const pageResourceType = getResourceTypeForPath(location.pathname);
        const access = getBannerAccess(receivedGrants, selectedUserId ?? '', pageResourceType);
        const sectionLabel = pageResourceType
          ? (RESOURCE_TYPE_LABELS[pageResourceType] ?? pageResourceType)
          : 'Data';
        const viewedName = getUserName(selectedUserId ?? '');

        // Household members always have at least read access — 'none' (no explicit grant)
        // still means read-only, not blocked.
        const canWrite = access === 'write';
        const bannerConfig = canWrite
          ? {
              bg: 'bg.success', border: 'border.default',
              headColor: 'text.primary', textColor: 'text.heading',
              icon: '✏️', prefix: 'Can Edit:', suffix: `'s ${sectionLabel}`,
            }
          : {
              bg: 'bg.info', border: 'border.default',
              headColor: 'text.primary', textColor: 'text.heading',
              icon: '👁️', prefix: 'Read Only:', suffix: `'s ${sectionLabel}`,
            };

        return (
          <Box bg={bannerConfig.bg} borderBottomWidth={1} borderColor={bannerConfig.border} px={8} py={2}>
            <HStack spacing={3}>
              <Text fontSize="sm" fontWeight="semibold" color={bannerConfig.headColor}>
                {bannerConfig.icon} {bannerConfig.prefix}
              </Text>
              <Badge size="sm" fontSize="xs" px={2} py={1} borderRadius="md"
                bg={getUserColor(selectedUserId ?? '')} color="white" fontWeight="bold">
                {getUserInitials(selectedUserId ?? '')}
              </Badge>
              <Text fontSize="sm" fontWeight="medium" color={bannerConfig.textColor}>
                {viewedName}{bannerConfig.suffix}
              </Text>
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
                <Text
                  fontSize="md"
                  fontWeight="bold"
                  color={
                    dashboardSummary.net_worth >= 0 ? "finance.positive" : "finance.negative"
                  }
                >
                  {formatCurrency(Number(dashboardSummary.net_worth))}
                </Text>
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
                          <ChevronRightIcon boxSize={3.5} color="text.secondary" />
                        ) : (
                          <ChevronDownIcon boxSize={3.5} color="text.secondary" />
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
                        color={groupTotal < 0 ? "finance.negative" : "text.primary"}
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
                <Text fontSize="sm" color="text.muted" textAlign="center" py={8}>
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
          <Outlet />
        </Box>
      </Flex>

      {/* Add Account Modal */}
      <AddAccountModal isOpen={isAddAccountOpen} onClose={onAddAccountClose} />
    </Flex>
  );
};
