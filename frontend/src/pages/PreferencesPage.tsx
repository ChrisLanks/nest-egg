import { useState, useEffect } from "react";

const getDaysInMonth = (year: number | null, month: number | null): number => {
  if (!month) return 31;
  const y = year ?? 2001; // use non-leap reference year when year is unknown
  return new Date(y, month, 0).getDate();
};
import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  Box,
  Button,
  ButtonGroup,
  Collapse,
  Container,
  Divider,
  FormControl,
  FormLabel,
  Heading,
  Icon,
  Input,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Text,
  useDisclosure,
  useToast,
  VStack,
  FormHelperText,
  HStack,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { ChevronDownIcon, ChevronRightIcon } from "@chakra-ui/icons";
import { FiSun, FiMoon, FiMonitor } from "react-icons/fi";
import {
  useColorModePreference,
  type ColorModePreference,
} from "../hooks/useColorModePreference";
import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../services/api";
import {
  useNavDefaults,
  NAV_SECTIONS as NAV_SECTIONS_FROM_HOOK,
} from "../hooks/useNavDefaults";
import { useAuthStore } from "../features/auth/stores/authStore";
import HelpHint from "../components/HelpHint";
import { helpContent } from "../constants/helpContent";

interface UpdateProfileData {
  display_name?: string;
  email?: string;
  current_password?: string;
  birth_day?: number | null;
  birth_month?: number | null;
  birth_year?: number | null;
  state_of_residence?: string | null;
  target_retirement_state?: string | null;
}

interface ChangePasswordData {
  current_password: string;
  new_password: string;
}

type NotificationPrefs = {
  account_syncs?: boolean;
  account_activity?: boolean;
  budget_alerts?: boolean;
  goal_alerts?: boolean;
  milestones?: boolean;
  household?: boolean;
  weekly_recap?: boolean;
  equity_alerts?: boolean;
  crypto_alerts?: boolean;
  bond_alerts?: boolean;
  planning_alerts?: boolean;
  portfolio_alerts?: boolean;
};

const NOTIFICATION_CATEGORIES: {
  key: keyof NotificationPrefs;
  label: string;
  description: string;
}[] = [
  {
    key: "account_syncs",
    label: "Account Syncs",
    description:
      "Sync failures, re-authentication required, and stale account warnings.",
  },
  {
    key: "account_activity",
    label: "Account Activity",
    description:
      "New accounts connected, large transactions, and duplicate detection.",
  },
  {
    key: "budget_alerts",
    label: "Budget Alerts",
    description: "Notifications when you approach or exceed budget thresholds.",
  },
  {
    key: "goal_alerts",
    label: "Goal Alerts",
    description:
      "Notifications when you reach a savings goal or mark one as funded.",
  },
  {
    key: "milestones",
    label: "Milestones & FIRE",
    description:
      "Portfolio milestones, all-time highs, Coast FI, and FI achievement.",
  },
  {
    key: "household",
    label: "Household",
    description: "Members joining or leaving, and retirement scenario updates.",
  },
  {
    key: "weekly_recap",
    label: "Weekly Recap",
    description:
      "Monday morning digest of your spending, income, and net worth for the past week.",
  },
  {
    key: "equity_alerts",
    label: "Equity & RSU Alerts",
    description:
      "Notifications when equity holdings vest or price refreshes exceed thresholds.",
  },
  {
    key: "crypto_alerts",
    label: "Crypto Price Alerts",
    description: "Price movement alerts for tracked cryptocurrency holdings.",
  },
  {
    key: "bond_alerts",
    label: "Bond & Treasury Alerts",
    description: "Upcoming I-Bond, T-Bill, T-Note, and TIPS maturity reminders.",
  },
  {
    key: "planning_alerts",
    label: "Planning Alerts",
    description:
      "Missing beneficiary designations, pension election deadlines, and QCD opportunities.",
  },
  {
    key: "portfolio_alerts",
    label: "Portfolio Alerts",
    description:
      "Rebalance drift, tax bucket imbalance, and tax-loss harvesting opportunities.",
  },
];

function EmailNotificationsSection() {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Check if email is configured on the server
  const { data: emailConfig } = useQuery({
    queryKey: ["emailConfigured"],
    queryFn: async () => {
      const response = await api.get("/settings/email-configured");
      return response.data as { configured: boolean };
    },
  });

  // Fetch current profile (includes email_notifications_enabled + notification_preferences)
  const { data: profile, isLoading } = useQuery({
    queryKey: ["notificationPrefsProfile"],
    queryFn: async () => {
      const response = await api.get("/settings/profile");
      return response.data as {
        email_notifications_enabled: boolean;
        notification_preferences: NotificationPrefs | null;
      };
    },
  });

  const emailPref = profile?.email_notifications_enabled ?? true;
  const categoryPrefs: NotificationPrefs =
    profile?.notification_preferences ?? {};

  const emailToggleMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      const response = await api.patch("/settings/email-notifications", null, {
        params: { enabled },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["notificationPrefsProfile"] });
      toast({
        title: data.email_notifications_enabled
          ? "Email notifications enabled"
          : "Email notifications disabled",
        status: "success",
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: "Failed to update preference",
        status: "error",
        duration: 3000,
      });
    },
  });

  const categoryMutation = useMutation({
    mutationFn: async (update: Partial<NotificationPrefs>) => {
      const response = await api.patch(
        "/settings/notification-preferences",
        update,
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notificationPrefsProfile"] });
    },
    onError: () => {
      toast({
        title: "Failed to save preference",
        status: "error",
        duration: 3000,
      });
    },
  });

  return (
    <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
      <Heading size="md" mb={1}>
        Notifications
      </Heading>
      <Text color="text.secondary" fontSize="sm" mb={4}>
        Control which notifications you see and how you receive them.
      </Text>

      <VStack spacing={4} align="stretch">
        {/* Global email toggle — only shown when SMTP is configured */}
        {emailConfig?.configured && (
          <FormControl>
            <HStack justify="space-between">
              <Box>
                <FormLabel mb={0}>Email Notifications</FormLabel>
                <FormHelperText mt={0}>
                  Receive email alerts for important events.
                </FormHelperText>
              </Box>
              <Switch
                isChecked={emailPref}
                isDisabled={isLoading || emailToggleMutation.isPending}
                onChange={(e) => emailToggleMutation.mutate(e.target.checked)}
                colorScheme="brand"
              />
            </HStack>
          </FormControl>
        )}

        {/* Per-category in-app toggles */}
        <Box>
          <Text fontWeight="medium" fontSize="sm" mb={3}>
            Notification categories
          </Text>
          <VStack spacing={3} align="stretch">
            {NOTIFICATION_CATEGORIES.map(({ key, label, description }) => {
              const enabled = categoryPrefs[key] !== false; // default true if missing
              return (
                <FormControl key={key}>
                  <HStack justify="space-between" align="start">
                    <Box flex={1}>
                      <FormLabel mb={0} fontSize="sm">
                        {label}
                      </FormLabel>
                      <FormHelperText mt={0} fontSize="xs">
                        {description}
                      </FormHelperText>
                    </Box>
                    <Switch
                      isChecked={enabled}
                      isDisabled={isLoading || categoryMutation.isPending}
                      onChange={(e) =>
                        categoryMutation.mutate({ [key]: e.target.checked })
                      }
                      colorScheme="brand"
                      size="sm"
                      mt={1}
                    />
                  </HStack>
                </FormControl>
              );
            })}
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

// NAV_SECTIONS and NavItem/NavSection types are imported from useNavDefaults hook
const NAV_SECTIONS = NAV_SECTIONS_FROM_HOOK;

function NavigationVisibilitySection() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [pendingReload, setPendingReload] = useState(false);
  // Account/age-aware defaults — same logic as Layout so the toggles reflect
  // the real nav state (e.g. mortgage shows as "on" when user has a mortgage)
  const { conditionalDefaults } = useNavDefaults();

  // Paths controlled by the "Show advanced features" master toggle
  // Must match every item with advanced: true in NAV_SECTIONS (useNavDefaults.ts)
  const ADVANCED_PATHS = [
    "/investment-tools",
    "/tax-center",
  ];

  // Single source of truth: per-item overrides from nest-egg-nav-visibility.
  // The advanced master switch reads from and writes into this same store,
  // so the per-item switches immediately reflect the master toggle state.
  const [overrides, setOverrides] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem("nest-egg-nav-visibility");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  // Master "show advanced" is true when ALL advanced paths are explicitly on
  const showAdvanced = ADVANCED_PATHS.every((p) => overrides[p] === true);

  const persistOverrides = (next: Record<string, boolean>) => {
    setOverrides(next);
    try {
      if (Object.keys(next).length === 0) {
        localStorage.removeItem("nest-egg-nav-visibility");
      } else {
        localStorage.setItem("nest-egg-nav-visibility", JSON.stringify(next));
      }
    } catch {
      /* ignore */
    }
  };

  const toggleAdvanced = (next: boolean) => {
    const updated = { ...overrides };
    for (const path of ADVANCED_PATHS) {
      updated[path] = next;
    }
    persistOverrides(updated);
    // Sync legacy flag read by Layout's toggle button
    try {
      localStorage.setItem("nest-egg-show-advanced-nav", String(next));
    } catch {
      /* ignore */
    }
    // Persist to server so the preference survives across devices
    api.patch("/settings/profile", { show_advanced_nav: next }).catch(() => {
      /* non-critical — localStorage is the immediate source of truth */
    });
    // Reload so the top-nav dropdowns reflect the change immediately
    window.location.reload();
  };

  const toggleItem = (path: string, checked: boolean) => {
    persistOverrides({ ...overrides, [path]: checked });
    setPendingReload(true);
  };

  const resetToDefaults = () => {
    persistOverrides({});
    // Also remove the legacy keys if present
    try {
      localStorage.removeItem("nest-egg-show-all-nav");
      localStorage.removeItem("nest-egg-show-advanced-nav");
    } catch {
      /* ignore */
    }
    window.location.reload();
  };

  const hasOverrides = Object.keys(overrides).length > 0;

  const isItemOn = (item: {
    path: string;
    alwaysOn?: boolean;
    conditional?: boolean;
    advanced?: boolean;
  }): boolean => {
    if (item.alwaysOn) return true;
    if (item.path in overrides) return overrides[item.path];
    // Advanced items default to off — they're gated by the master toggle, not accounts
    if (item.advanced) return false;
    // Use account/age-aware defaults so e.g. mortgage shows as "on"
    // when the user actually has a mortgage account
    return conditionalDefaults[item.path] ?? true;
  };

  return (
    <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
      {/* Clickable header — styled as a button so it's obviously interactive */}
      <HStack
        justify="space-between"
        cursor="pointer"
        onClick={() => setIsExpanded((v) => !v)}
        userSelect="none"
        p={2}
        mx={-2}
        borderRadius="md"
        _hover={{ bg: "bg.subtle" }}
        transition="background 0.15s"
      >
        <HStack spacing={3}>
          <Icon
            as={isExpanded ? ChevronDownIcon : ChevronRightIcon}
            boxSize={5}
            color="brand.500"
          />
          <Box>
            <Heading size="md">Navigation</Heading>
            <Text fontSize="xs" color="text.muted" mt={0.5}>
              {isExpanded
                ? "Click to collapse"
                : "Click to customize which tabs are visible"}
            </Text>
          </Box>
        </HStack>
        <HStack spacing={2}>
          {hasOverrides && (
            <Button
              size="xs"
              variant="outline"
              colorScheme="gray"
              onClick={(e) => {
                e.stopPropagation();
                resetToDefaults();
              }}
            >
              Reset to Default
            </Button>
          )}
        </HStack>
      </HStack>

      {/* Advanced features master toggle — always visible, no need to expand */}
      <HStack justify="space-between" mt={3} px={1}>
        <Box>
          <Text fontSize="sm" fontWeight="medium">
            Show advanced features
          </Text>
          <Text fontSize="xs" color="text.muted">
            Unlocks Tax Center (tax projection, Roth conversion, IRMAA, withholding) and Planning Tools (FIRE, loan modeler, HSA optimizer, bond ladder, what-if scenarios). Individual tabs can still be toggled below.
          </Text>
        </Box>
        <Switch
          isChecked={showAdvanced}
          onChange={(e) => toggleAdvanced(e.target.checked)}
          colorScheme="brand"
        />
      </HStack>

      <Collapse in={isExpanded} animateOpacity>
        <VStack align="stretch" spacing={4} mt={4}>
          {NAV_SECTIONS.map((section) => (
            <Box key={section.group}>
              <Text
                fontSize="xs"
                fontWeight="bold"
                textTransform="uppercase"
                color="text.muted"
                mb={2}
              >
                {section.group}
              </Text>
              <VStack align="stretch" spacing={1}>
                {section.items.map((item) => {
                  const isOn = isItemOn(item);
                  const isOverridden = item.path in overrides;
                  const isAutoControlled =
                    (item.conditional || item.advanced) && !isOverridden;
                  return (
                    <HStack
                      key={item.path}
                      justify="space-between"
                      px={3}
                      py={2}
                      borderRadius="md"
                      _hover={item.alwaysOn ? undefined : { bg: "bg.subtle" }}
                    >
                      <Box flex={1}>
                        <HStack spacing={2}>
                          <Text fontSize="sm" fontWeight="medium">
                            {item.label}
                          </Text>
                          {item.alwaysOn && (
                            <Text fontSize="xs" color="text.muted">
                              always on
                            </Text>
                          )}
                          {isOverridden && !item.alwaysOn && (
                            <Text fontSize="xs" color="brand.500">
                              overridden
                            </Text>
                          )}
                        </HStack>
                        {(item as any).reason && (
                          <Text fontSize="xs" color="text.muted" mt={0.5}>
                            {isAutoControlled
                              ? (item as any).reason
                              : isOn
                                ? "Manually enabled"
                                : "Manually hidden"}
                          </Text>
                        )}
                      </Box>
                      <Switch
                        size="sm"
                        isChecked={isOn}
                        isDisabled={item.alwaysOn}
                        onChange={(e) => {
                          if (item.alwaysOn) return;
                          toggleItem(item.path, e.target.checked);
                        }}
                        colorScheme="brand"
                      />
                    </HStack>
                  );
                })}
              </VStack>
            </Box>
          ))}
        </VStack>
        {pendingReload ? (
          <HStack mt={3} justify="flex-end">
            <Text fontSize="xs" color="text.muted">
              Reload to see changes in the nav bar
            </Text>
            <Button
              size="xs"
              colorScheme="brand"
              onClick={() => window.location.reload()}
            >
              Apply
            </Button>
          </HStack>
        ) : (
          <Text fontSize="xs" color="text.muted" mt={3}>
            Toggle tabs above, then click Apply to update the nav bar.
          </Text>
        )}
      </Collapse>
    </Box>
  );
}

export default function PreferencesPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { logout } = useAuthStore();
  const {
    preference: colorModePreference,
    setPreference: setColorModePreference,
  } = useColorModePreference();

  // Note: Preferences are always for the current logged-in user,
  // not the selected user view. This page shows YOUR settings.

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [originalEmail, setOriginalEmail] = useState("");
  const [emailConfirmPassword, setEmailConfirmPassword] = useState("");
  const [birthDay, setBirthDay] = useState<number | null>(null);
  const [birthMonth, setBirthMonth] = useState<number | null>(null);
  const [birthYear, setBirthYear] = useState<number | null>(null);
  const [defaultCurrency, setDefaultCurrency] = useState("USD");
  const [stateOfResidence, setStateOfResidence] = useState<string>("");
  const [targetRetirementState, setTargetRetirementState] = useState<string>("");

  // Password state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Fetch user profile
  const { data: profileData, isLoading: profileLoading, isError: profileError } = useQuery({
    queryKey: ["userProfile"],
    queryFn: async () => {
      const response = await api.get("/settings/profile");
      return response.data;
    },
  });

  // Seed form state whenever profile data arrives (first load or cache hit).
  // Using useEffect ensures the form populates even when React Query serves
  // cached data without re-running the queryFn.
  useEffect(() => {
    if (!profileData) return;
    // display_name is primary; fall back to first+last for existing users
    setDisplayName(
      profileData.display_name ||
        `${profileData.first_name || ""} ${profileData.last_name || ""}`.trim() ||
        "",
    );
    setEmail(profileData.email || "");
    setOriginalEmail(profileData.email || "");
    setBirthDay(profileData.birth_day || null);
    setBirthMonth(profileData.birth_month || null);
    setBirthYear(profileData.birth_year || null);
    setDefaultCurrency(profileData.default_currency || "USD");
    setStateOfResidence(profileData.state_of_residence || "");
    setTargetRetirementState(profileData.target_retirement_state || "");
  }, [profileData]);

  // Fetch state list for dropdowns
  const { data: statesData } = useQuery({
    queryKey: ["stateList"],
    queryFn: async () => {
      const response = await api.get("/settings/financial-constants/states");
      return response.data.states as Array<{
        code: string;
        name: string;
        income_tax_rate: number;
        no_income_tax: boolean;
      }>;
    },
    staleTime: Infinity,
  });

  // Update profile mutation
  const updateProfileMutation = useMutation({
    mutationFn: async (data: UpdateProfileData) => {
      const response = await api.patch("/settings/profile", data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["userProfile"] });
      if (variables.email && variables.email !== originalEmail) {
        setOriginalEmail(variables.email);
        setEmailConfirmPassword("");
      }
      toast({
        title: "Profile updated",
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      let description = "An error occurred";
      if (typeof detail === "string") description = detail;
      else if (Array.isArray(detail))
        description = detail[0]?.msg || "Validation error";
      else if (detail?.message) description = detail.message;
      toast({
        title: "Failed to update profile",
        description,
        status: "error",
        duration: 5000,
      });
    },
  });

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: async (data: ChangePasswordData) => {
      const response = await api.post(
        "/settings/profile/change-password",
        data,
      );
      return response.data;
    },
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast({
        title: "Password changed successfully",
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail;
      let title = "Failed to change password";
      let description: any = "An error occurred";
      if (typeof detail === "string") {
        description = detail;
      } else if (Array.isArray(detail)) {
        description = detail[0]?.msg || "Validation error";
      } else if (detail && typeof detail === "object") {
        const errors: string[] = Array.isArray(detail.errors)
          ? detail.errors
          : [];
        if (errors.length > 0) {
          // Password validation error: message is a human-readable title, errors are the reasons
          if (detail.message) title = detail.message;
          description = (
            <VStack align="start" spacing={1} mt={1}>
              {errors.map((msg: string, i: number) => (
                <Text key={i} fontSize="sm">
                  • {msg}
                </Text>
              ))}
            </VStack>
          );
        } else {
          // Rate limit, auth errors, etc.: keep generic title, show message as description
          description = detail.message || detail.error || "An error occurred";
        }
      }
      toast({ title, description, status: "error", duration: 8000 });
    },
  });

  // Export state
  const [isExporting, setIsExporting] = useState(false);

  // Delete account state
  const {
    isOpen: isDeleteOpen,
    onOpen: onDeleteOpen,
    onClose: onDeleteClose,
  } = useDisclosure();
  const [deletePassword, setDeletePassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const cancelDeleteRef = useRef<HTMLButtonElement>(null);

  const handleDeleteAccount = async () => {
    if (!deletePassword) return;
    setIsDeleting(true);
    try {
      await api.delete("/settings/account", {
        data: { password: deletePassword },
      });
      // Clear auth state before redirect so no stale tokens remain in memory
      logout();
      window.location.href = "/login";
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const description =
        typeof detail === "string" ? detail : "An error occurred";
      toast({
        title: "Failed to delete account",
        description,
        status: "error",
        duration: 5000,
      });
    } finally {
      setIsDeleting(false);
      setDeletePassword("");
      onDeleteClose();
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const response = await api.get("/settings/export", {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      const today = new Date().toISOString().slice(0, 10);
      link.setAttribute("download", `nest-egg-export-${today}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast({ title: "Export downloaded", status: "success", duration: 3000 });
    } catch {
      toast({ title: "Export failed", status: "error", duration: 3000 });
    } finally {
      setIsExporting(false);
    }
  };

  const handleUpdateProfile = () => {
    const emailChanged = email !== originalEmail;
    if (emailChanged && !emailConfirmPassword) {
      toast({
        title: "Password required",
        description: "Enter your current password to confirm the email change.",
        status: "error",
        duration: 4000,
      });
      return;
    }
    updateProfileMutation.mutate({
      display_name: displayName,
      email: email,
      current_password: emailChanged ? emailConfirmPassword : undefined,
      birth_day: birthDay,
      birth_month: birthMonth,
      birth_year: birthYear,
      state_of_residence: stateOfResidence || null,
      target_retirement_state: targetRetirementState || null,
    });
  };

  const handleChangePassword = () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: "Passwords do not match",
        status: "error",
        duration: 3000,
      });
      return;
    }

    if (newPassword.length < 12) {
      toast({
        title: "Password must be at least 12 characters",
        status: "error",
        duration: 3000,
      });
      return;
    }

    changePasswordMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

  if (profileLoading) {
    return (
      <Container maxW="container.lg" py={8}>
        <VStack spacing={4}>
          <Skeleton height="40px" />
          <Skeleton height="40px" />
          <Skeleton height="40px" />
        </VStack>
      </Container>
    );
  }

  if (profileError) {
    return (
      <Container maxW="container.lg" py={8}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          Failed to load preferences. Please refresh and try again.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        <Heading size="lg">Settings</Heading>

        {/* User Profile Section */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={4}>
            User Profile
          </Heading>
          <Stack spacing={4}>
            <FormControl>
              <FormLabel>Name</FormLabel>
              <Input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="How you'd like to appear"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Email</FormLabel>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
              />
            </FormControl>

            {email !== originalEmail && (
              <FormControl isRequired>
                <FormLabel>Confirm password to change email</FormLabel>
                <Input
                  type="password"
                  value={emailConfirmPassword}
                  onChange={(e) => setEmailConfirmPassword(e.target.value)}
                  placeholder="Your current password"
                  autoComplete="current-password"
                />
                <FormHelperText>
                  For security, confirm your password before changing your email address.
                </FormHelperText>
              </FormControl>
            )}

            {/* State of Residence */}
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              <FormControl>
                <FormLabel>State of Residence</FormLabel>
                <Select
                  value={stateOfResidence}
                  onChange={(e) => setStateOfResidence(e.target.value)}
                  placeholder="Select state"
                >
                  {(statesData ?? []).map((s) => (
                    <option key={s.code} value={s.code}>
                      {s.name}{s.no_income_tax ? " (no income tax)" : ` (${(s.income_tax_rate * 100).toFixed(1)}%)`}
                    </option>
                  ))}
                </Select>
                <FormHelperText>
                  Used for state tax estimates in Tax Projection, FIRE metrics,
                  and other tools. Each household member sets their own state.
                </FormHelperText>
              </FormControl>

              <FormControl>
                <FormLabel>Planned Retirement State</FormLabel>
                <Select
                  value={targetRetirementState}
                  onChange={(e) => setTargetRetirementState(e.target.value)}
                  placeholder="Same as current"
                >
                  {(statesData ?? []).map((s) => (
                    <option key={s.code} value={s.code}>
                      {s.name}{s.no_income_tax ? " (no income tax)" : ` (${(s.income_tax_rate * 100).toFixed(1)}%)`}
                    </option>
                  ))}
                </Select>
                <FormHelperText>
                  If you plan to move states in retirement (e.g., from CA to FL),
                  this is used to estimate your post-retirement state tax burden.
                </FormHelperText>
              </FormControl>
            </SimpleGrid>

            <FormControl>
              <FormLabel>Birthday</FormLabel>
              <SimpleGrid columns={3} spacing={2}>
                <Select
                  placeholder="Month"
                  value={birthMonth || ""}
                  onChange={(e) => {
                    const month = e.target.value
                      ? parseInt(e.target.value)
                      : null;
                    setBirthMonth(month);
                    // Clear day if it's now out of range for the new month
                    if (
                      birthDay &&
                      month &&
                      birthDay > getDaysInMonth(birthYear, month)
                    ) {
                      setBirthDay(null);
                    }
                  }}
                >
                  {[
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                  ].map((m, i) => (
                    <option key={i + 1} value={i + 1}>
                      {m}
                    </option>
                  ))}
                </Select>
                <Select
                  placeholder="Day"
                  value={birthDay || ""}
                  onChange={(e) =>
                    setBirthDay(
                      e.target.value ? parseInt(e.target.value) : null,
                    )
                  }
                >
                  {Array.from(
                    { length: getDaysInMonth(birthYear, birthMonth) },
                    (_, i) => (
                      <option key={i + 1} value={i + 1}>
                        {i + 1}
                      </option>
                    ),
                  )}
                </Select>
                <NumberInput
                  value={birthYear || ""}
                  onChange={(_, value) => {
                    const year = isNaN(value) ? null : value;
                    setBirthYear(year);
                    // Clear day if Feb 29 becomes invalid (non-leap year)
                    if (
                      birthDay &&
                      birthMonth &&
                      birthDay > getDaysInMonth(year, birthMonth)
                    ) {
                      setBirthDay(null);
                    }
                  }}
                  min={1900}
                  max={new Date().getFullYear()}
                >
                  <NumberInputField placeholder="Year" />
                </NumberInput>
              </SimpleGrid>
              <FormHelperText>
                Used for retirement planning (59½ rule, RMDs).
                <HelpHint hint={helpContent.preferences.birthYear} /> Leave all
                blank to hide.
              </FormHelperText>
            </FormControl>

            <Button
              colorScheme="blue"
              onClick={handleUpdateProfile}
              isLoading={updateProfileMutation.isPending}
              alignSelf="flex-start"
            >
              Save Profile
            </Button>
          </Stack>
        </Box>

        {/* Appearance Section */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={1}>
            Appearance
          </Heading>
          <Text color="text.secondary" fontSize="sm" mb={4}>
            Choose your preferred color scheme.
          </Text>
          <ButtonGroup size="sm" isAttached variant="outline">
            {[
              {
                value: "light" as ColorModePreference,
                label: "Light",
                icon: FiSun,
              },
              {
                value: "dark" as ColorModePreference,
                label: "Dark",
                icon: FiMoon,
              },
              {
                value: "system" as ColorModePreference,
                label: "System",
                icon: FiMonitor,
              },
            ].map(({ value, label, icon }) => (
              <Button
                key={value}
                onClick={() => setColorModePreference(value)}
                variant={colorModePreference === value ? "solid" : "outline"}
                colorScheme={colorModePreference === value ? "brand" : "gray"}
                leftIcon={<Icon as={icon} />}
              >
                {label}
              </Button>
            ))}
          </ButtonGroup>
        </Box>

        {/* Regional Settings */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={1}>
            Regional Settings
          </Heading>
          <Text color="text.secondary" fontSize="sm" mb={4}>
            Configure currency display and regional preferences.
          </Text>
          <FormControl>
            <FormLabel>Default Currency</FormLabel>
            <Select
              value={defaultCurrency}
              onChange={(e) => setDefaultCurrency(e.target.value)}
              maxW="200px"
            >
              <option value="USD">USD - US Dollar</option>
              <option value="EUR">EUR - Euro</option>
              <option value="GBP">GBP - British Pound</option>
              <option value="CAD">CAD - Canadian Dollar</option>
              <option value="AUD">AUD - Australian Dollar</option>
              <option value="JPY">JPY - Japanese Yen</option>
              <option value="CHF">CHF - Swiss Franc</option>
              <option value="INR">INR - Indian Rupee</option>
              <option value="CNY">CNY - Chinese Yuan</option>
              <option value="BRL">BRL - Brazilian Real</option>
            </Select>
            <FormHelperText>
              Inflation adjustments can be configured per retirement scenario in
              Retirement Planning.
            </FormHelperText>
          </FormControl>
          <Button
            colorScheme="blue"
            size="sm"
            mt={4}
            onClick={() =>
              updateProfileMutation.mutate({
                default_currency: defaultCurrency,
              } as any)
            }
            isLoading={updateProfileMutation.isPending}
          >
            Save Regional Settings
          </Button>
        </Box>

        {/* Email Notifications Section */}
        <EmailNotificationsSection />

        {/* Change Password Section */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={4}>
            Change Password
          </Heading>
          <Stack spacing={4}>
            <FormControl>
              <FormLabel>Current Password</FormLabel>
              <Input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
              />
            </FormControl>

            <FormControl>
              <FormLabel>New Password</FormLabel>
              <Input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
              />
              <FormHelperText>Must be at least 12 characters</FormHelperText>
            </FormControl>

            <FormControl>
              <FormLabel>Confirm New Password</FormLabel>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
              />
            </FormControl>

            <Button
              colorScheme="blue"
              onClick={handleChangePassword}
              isLoading={changePasswordMutation.isPending}
              alignSelf="flex-start"
            >
              Change Password
            </Button>
          </Stack>
        </Box>

        {/* Navigation Section (collapsible) */}
        <NavigationVisibilitySection />

        {/* Export Data Section */}
        <Box bg="bg.surface" p={6} borderRadius="lg" boxShadow="sm">
          <Heading size="md" mb={1}>
            Export Data
          </Heading>
          <Text color="text.secondary" fontSize="sm" mb={4}>
            Download all your accounts, transactions, and holdings as a ZIP of
            CSV files.
          </Text>
          <Button
            colorScheme="blue"
            variant="outline"
            onClick={handleExport}
            isLoading={isExporting}
            loadingText="Preparing export…"
          >
            Download CSV Export
          </Button>
        </Box>

        {/* Danger Zone — Delete Account */}
        <Box
          bg="bg.surface"
          p={6}
          borderRadius="lg"
          boxShadow="sm"
          borderWidth={1}
          borderColor="red.200"
        >
          <Heading size="md" mb={1} color="red.600">
            Danger Zone
          </Heading>
          <Text color="text.secondary" fontSize="sm" mb={4}>
            Permanently delete your account and all associated data. This action
            cannot be undone.
          </Text>
          <Divider mb={4} />
          <Button colorScheme="red" variant="outline" onClick={onDeleteOpen}>
            Delete Account
          </Button>
        </Box>

        {/* Delete Account confirmation dialog */}
        <AlertDialog
          isOpen={isDeleteOpen}
          leastDestructiveRef={cancelDeleteRef}
          onClose={onDeleteClose}
        >
          <AlertDialogOverlay>
            <AlertDialogContent>
              <AlertDialogHeader fontSize="lg" fontWeight="bold">
                Delete Account
              </AlertDialogHeader>

              <AlertDialogBody>
                <Text mb={4}>
                  This will permanently delete your account and{" "}
                  <strong>all associated data</strong> (accounts, transactions,
                  holdings). This cannot be undone.
                </Text>
                <FormControl>
                  <FormLabel>Confirm your password</FormLabel>
                  <Input
                    type="password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    placeholder="Enter your password to confirm"
                    autoComplete="current-password"
                  />
                </FormControl>
              </AlertDialogBody>

              <AlertDialogFooter>
                <Button ref={cancelDeleteRef} onClick={onDeleteClose}>
                  Cancel
                </Button>
                <Button
                  colorScheme="red"
                  ml={3}
                  isLoading={isDeleting}
                  isDisabled={!deletePassword}
                  onClick={handleDeleteAccount}
                >
                  Delete My Account
                </Button>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialogOverlay>
        </AlertDialog>
      </VStack>
    </Container>
  );
}
