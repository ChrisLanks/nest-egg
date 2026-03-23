/**
 * Household Settings Page
 *
 * Manage household members, send invitations, and view pending invites.
 */

import {
  Box,
  Container,
  Heading,
  VStack,
  HStack,
  Text,
  Button,
  Card,
  CardBody,
  CardHeader,
  Avatar,
  Badge,
  IconButton,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Stack,
  FormErrorMessage,
  Select,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from "@chakra-ui/react";
import {
  EmailIcon,
  DeleteIcon,
  CopyIcon,
  CheckIcon,
  CheckCircleIcon,
} from "@chakra-ui/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useRef, useEffect } from "react";
import api from "../services/api";
import { useAuthStore } from "../features/auth/stores/authStore";
import {
  guestAccessApi,
  type GuestRecord,
  type GuestInvitation as GuestAccessInvitation,
} from "../api/guest-access";
import { getErrorMessage } from "../utils/errorHandling";
import { validateEmail as sharedValidateEmail } from "../utils/validation";

/** Short human-readable hint about whether an email was sent. */
const email_configured_hint = (inv: Invitation) =>
  `Invitation created. ${inv.join_url ? "Share the join link if the invitee doesn't receive an email." : ""}`;

interface HouseholdMember {
  id: string;
  email: string;
  display_name?: string;
  first_name?: string;
  last_name?: string;
  is_org_admin: boolean;
  is_primary_household_member: boolean;
  created_at: string;
}

interface Invitation {
  id: string;
  email: string;
  invitation_code: string;
  status: "pending" | "accepted" | "declined" | "expired";
  expires_at: string;
  created_at: string;
  invited_by_email: string;
  join_url: string;
}

interface OrganizationPreferences {
  id: string;
  name: string;
  monthly_start_day: number;
  timezone: string;
}

/** Small copy-to-clipboard button for an invitation join URL. */
const CopyLinkButton: React.FC<{ url: string }> = ({ url }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };
  return (
    <Button
      size="xs"
      variant="ghost"
      colorScheme="blue"
      leftIcon={copied ? <CheckIcon /> : <CopyIcon />}
      onClick={handleCopy}
    >
      {copied ? "Copied!" : "Copy link"}
    </Button>
  );
};

export const HouseholdSettingsPage: React.FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isLeaveOpen,
    onOpen: onLeaveOpen,
    onClose: onLeaveClose,
  } = useDisclosure();
  const {
    isOpen: isCelebrationOpen,
    onOpen: onCelebrationOpen,
    onClose: onCelebrationClose,
  } = useDisclosure();
  const leaveCancelRef = useRef<HTMLButtonElement>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [celebrationEmail, setCelebrationEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  // Guest access state
  const {
    isOpen: isGuestInviteOpen,
    onOpen: onGuestInviteOpen,
    onClose: onGuestInviteClose,
  } = useDisclosure();
  const [guestEmail, setGuestEmail] = useState("");
  const [guestRole, setGuestRole] = useState<"viewer" | "advisor">("viewer");
  const [guestLabel, setGuestLabel] = useState("");
  const [guestEmailError, setGuestEmailError] = useState("");
  const [guestExpiresDays, setGuestExpiresDays] = useState<string>("");
  const { user, logout } = useAuthStore();
  const [monthlyStartDay, setMonthlyStartDay] = useState(1);
  // Reusable confirmation dialog state
  const {
    isOpen: isConfirmOpen,
    onOpen: onConfirmOpen,
    onClose: onConfirmClose,
  } = useDisclosure();
  const confirmCancelRef = useRef<HTMLButtonElement>(null);
  const [confirmConfig, setConfirmConfig] = useState<{
    title: string;
    body: string;
    confirmLabel: string;
    colorScheme: string;
    onConfirm: () => void;
  }>({
    title: "",
    body: "",
    confirmLabel: "Confirm",
    colorScheme: "red",
    onConfirm: () => {},
  });

  const openConfirmDialog = (config: {
    title: string;
    body: string;
    confirmLabel?: string;
    colorScheme?: string;
    onConfirm: () => void;
  }) => {
    setConfirmConfig({
      title: config.title,
      body: config.body,
      confirmLabel: config.confirmLabel || "Confirm",
      colorScheme: config.colorScheme || "red",
      onConfirm: config.onConfirm,
    });
    onConfirmOpen();
  };

  // Fetch household members
  const { data: members, isLoading: loadingMembers, isError: membersError } = useQuery<
    HouseholdMember[]
  >({
    queryKey: ["household-members"],
    queryFn: async () => {
      const response = await api.get("/household/members");
      return response.data;
    },
  });

  // Fetch pending invitations
  const { data: invitations, isLoading: loadingInvitations } = useQuery<
    Invitation[]
  >({
    queryKey: ["household-invitations"],
    queryFn: async () => {
      const response = await api.get("/household/invitations");
      return response.data;
    },
  });

  // Invite member mutation
  const inviteMutation = useMutation({
    mutationFn: async (email: string) => {
      const response = await api.post("/household/invite", { email });
      return response.data as Invitation;
    },
    onSuccess: (data) => {
      const isFirstInvite = !invitations || invitations.length === 0;
      toast({
        title: "Invitation sent",
        description: email_configured_hint(data),
        status: "success",
        duration: 5000,
      });
      const sentTo = inviteEmail;
      setInviteEmail("");
      onClose();
      queryClient.invalidateQueries({ queryKey: ["household-invitations"] });
      // Show celebration modal for first-ever invitation
      if (isFirstInvite) {
        setCelebrationEmail(sentTo);
        onCelebrationOpen();
      }
    },
    onError: (error: any) => {
      toast({
        title: "Failed to send invitation",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  // Remove member mutation
  const removeMutation = useMutation({
    mutationFn: async (memberId: string) => {
      await api.delete(`/household/members/${memberId}`);
    },
    onSuccess: () => {
      toast({
        title: "Member removed",
        description: "The member has been removed from the household.",
        status: "success",
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ["household-members"] });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to remove member",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  // Fetch org preferences
  const { data: orgPrefs } = useQuery<OrganizationPreferences>({
    queryKey: ["orgPreferences"],
    queryFn: async () => {
      const response = await api.get("/settings/organization");
      return response.data;
    },
    enabled: !!user,
  });

  // Sync monthlyStartDay when org preferences load or change
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (orgPrefs) {
      setMonthlyStartDay(orgPrefs.monthly_start_day || 1);
    }
  }, [orgPrefs]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Update org preferences mutation
  const updateOrgMutation = useMutation({
    mutationFn: async (data: { monthly_start_day: number }) => {
      const response = await api.patch("/settings/organization", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orgPreferences"] });
      toast({
        title: "Preferences updated",
        status: "success",
        duration: 3000,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update preferences",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  const handleUpdateOrgPreferences = () => {
    updateOrgMutation.mutate({ monthly_start_day: monthlyStartDay });
  };

  // Cancel invitation mutation
  const cancelInvitationMutation = useMutation({
    mutationFn: async (invitationId: string) => {
      await api.delete(`/household/invitations/${invitationId}`);
    },
    onSuccess: () => {
      toast({
        title: "Invitation cancelled",
        description: "The invitation has been cancelled.",
        status: "success",
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ["household-invitations"] });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to cancel invitation",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  // Update member role mutation (promote/demote)
  const updateRoleMutation = useMutation({
    mutationFn: async ({
      memberId,
      isAdmin,
    }: {
      memberId: string;
      isAdmin: boolean;
    }) => {
      await api.patch(`/household/members/${memberId}/role`, {
        is_admin: isAdmin,
      });
    },
    onSuccess: () => {
      toast({
        title: "Role updated",
        status: "success",
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ["household-members"] });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to update role",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  // Leave household mutation
  const leaveMutation = useMutation({
    mutationFn: async () => {
      await api.post("/household/leave");
    },
    onSuccess: () => {
      onLeaveClose();
      toast({
        title: "You have left the household",
        description: "Signing you out so your session refreshes.",
        status: "success",
        duration: 3000,
      });
      // Org context has changed — sign out so the user logs back in with fresh state
      setTimeout(() => {
        logout();
        window.location.href = "/login";
      }, 1500);
    },
    onError: (error: any) => {
      onLeaveClose();
      toast({
        title: "Failed to leave household",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  // --- Guest Access queries & mutations ---

  const { data: guestRecords, isLoading: loadingGuests } = useQuery<
    GuestRecord[]
  >({
    queryKey: ["guest-access-guests"],
    queryFn: guestAccessApi.listGuests,
    enabled: !!user?.is_org_admin,
  });

  const { data: guestInvitations } = useQuery<GuestAccessInvitation[]>({
    queryKey: ["guest-access-invitations"],
    queryFn: guestAccessApi.listInvitations,
    enabled: !!user?.is_org_admin,
  });

  const guestInviteMutation = useMutation({
    mutationFn: (data: {
      email: string;
      role: "viewer" | "advisor";
      label?: string;
    }) => guestAccessApi.invite(data),
    onSuccess: (result) => {
      if (result.email_delivered) {
        toast({
          title: "Guest invitation sent",
          description:
            "The guest will receive an email with instructions to join.",
          status: "success",
          duration: 5000,
        });
      } else {
        toast({
          title: "Invitation created — email delivery failed",
          description:
            "The invitation was created but we couldn't send the email. Share the join link manually.",
          status: "warning",
          duration: 10000,
          isClosable: true,
        });
      }
      setGuestEmail("");
      setGuestRole("viewer");
      setGuestLabel("");
      setGuestExpiresDays("");
      onGuestInviteClose();
      queryClient.invalidateQueries({
        queryKey: ["guest-access-invitations"],
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to invite guest",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  const revokeGuestMutation = useMutation({
    mutationFn: (guestId: string) => guestAccessApi.revokeGuest(guestId),
    onSuccess: () => {
      toast({
        title: "Guest access revoked",
        status: "success",
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ["guest-access-guests"] });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to revoke guest",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  const cancelGuestInvitationMutation = useMutation({
    mutationFn: (id: string) => guestAccessApi.cancelInvitation(id),
    onSuccess: () => {
      toast({
        title: "Guest invitation cancelled",
        status: "success",
        duration: 3000,
      });
      queryClient.invalidateQueries({
        queryKey: ["guest-access-invitations"],
      });
    },
    onError: (error: any) => {
      toast({
        title: "Failed to cancel invitation",
        description: getErrorMessage(error),
        status: "error",
        duration: 5000,
      });
    },
  });

  const handleGuestInvite = () => {
    const result = sharedValidateEmail(guestEmail);
    if (!result.valid) {
      setGuestEmailError(result.error);
      return;
    }
    setGuestEmailError("");
    guestInviteMutation.mutate({
      email: guestEmail,
      role: guestRole,
      label: guestLabel || undefined,
      access_expires_days: guestExpiresDays ? parseInt(guestExpiresDays, 10) : undefined,
    });
  };

  // Validate email
  const validateEmail = (email: string): boolean => {
    const result = sharedValidateEmail(email);
    if (!result.valid) {
      setEmailError(result.error);
      return false;
    }
    setEmailError("");
    return true;
  };

  // Handle invite submission
  const handleInvite = () => {
    if (validateEmail(inviteEmail)) {
      inviteMutation.mutate(inviteEmail);
    }
  };

  // Format display name
  const getDisplayName = (member: HouseholdMember): string => {
    if (member.display_name) return member.display_name;
    if (member.first_name && member.last_name) {
      return `${member.first_name} ${member.last_name}`;
    }
    if (member.first_name) return member.first_name;
    return member.email;
  };

  // Format date
  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        <Box>
          <Heading size="lg" mb={2}>
            Household Settings
          </Heading>
          <Text color="text.secondary">
            Manage household members and invitations
          </Text>
        </Box>

        {/* Household limit alert */}
        {members && members.length >= 5 && (
          <Alert status="warning">
            <AlertIcon />
            <Box>
              <AlertTitle>Household limit reached</AlertTitle>
              <AlertDescription>
                You have reached the maximum of 5 household members. Remove a
                member before inviting new ones.
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {/* Members section */}
        <Card>
          <CardHeader>
            <HStack justify="space-between">
              <Heading size="md">Household Members</Heading>
              {user?.is_org_admin && (
                <Button
                  leftIcon={<EmailIcon />}
                  colorScheme="blue"
                  size="sm"
                  onClick={onOpen}
                  isDisabled={members && members.length >= 5}
                >
                  Invite Member
                </Button>
              )}
            </HStack>
          </CardHeader>
          <CardBody>
            {loadingMembers ? (
              <HStack justify="center" py={8}>
                <Spinner />
              </HStack>
            ) : membersError ? (
              <Alert status="error" borderRadius="md">
                <AlertIcon />
                Failed to load household members. Please refresh and try again.
              </Alert>
            ) : (
              <VStack spacing={4} align="stretch">
                {members?.map((member) => (
                  <Card key={member.id} variant="outline">
                    <CardBody>
                      <HStack justify="space-between">
                        <HStack spacing={4}>
                          <Avatar name={getDisplayName(member)} size="md" />
                          <Box>
                            <HStack>
                              <Text fontWeight="medium">
                                {getDisplayName(member)}
                              </Text>
                              {member.id === user?.id && (
                                <Badge colorScheme="gray">You</Badge>
                              )}
                              {member.is_primary_household_member && (
                                <Badge colorScheme="purple">Primary</Badge>
                              )}
                              {member.is_org_admin && (
                                <Badge colorScheme="blue">Admin</Badge>
                              )}
                            </HStack>
                            <Text fontSize="sm" color="text.secondary">
                              {member.email}
                            </Text>
                            <Text fontSize="xs" color="text.muted">
                              Joined {formatDate(member.created_at)}
                            </Text>
                          </Box>
                        </HStack>
                        {member.id === user?.id &&
                        !member.is_primary_household_member ? (
                          <Text
                            fontSize="xs"
                            color="text.muted"
                            fontStyle="italic"
                            pr={1}
                          >
                            Use &quot;Leave Household&quot; below
                          </Text>
                        ) : member.id !== user?.id && user?.is_org_admin ? (
                          <HStack spacing={2}>
                            {!member.is_primary_household_member && (
                              <Button
                                size="xs"
                                variant="outline"
                                colorScheme={
                                  member.is_org_admin ? "orange" : "blue"
                                }
                                isLoading={updateRoleMutation.isPending}
                                onClick={() => {
                                  const name = getDisplayName(member);
                                  const promoting = !member.is_org_admin;
                                  openConfirmDialog({
                                    title: promoting
                                      ? `Promote ${name} to Admin?`
                                      : `Demote ${name} to Member?`,
                                    body: promoting
                                      ? `${name} will gain admin privileges including the ability to manage members, invitations, and household settings.`
                                      : `${name} will lose admin privileges and become a regular member.`,
                                    confirmLabel: promoting
                                      ? "Promote"
                                      : "Demote",
                                    colorScheme: promoting ? "blue" : "orange",
                                    onConfirm: () =>
                                      updateRoleMutation.mutate({
                                        memberId: member.id,
                                        isAdmin: promoting,
                                      }),
                                  });
                                }}
                              >
                                {member.is_org_admin
                                  ? "Demote to Member"
                                  : "Promote to Admin"}
                              </Button>
                            )}
                            {!member.is_primary_household_member && (
                              <IconButton
                                aria-label="Remove member"
                                icon={<DeleteIcon />}
                                colorScheme="red"
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const name = getDisplayName(member);
                                  openConfirmDialog({
                                    title: `Remove ${name}?`,
                                    body: `${name} will be removed from this household. Their accounts will be moved to a new solo household.`,
                                    confirmLabel: "Remove",
                                    colorScheme: "red",
                                    onConfirm: () =>
                                      removeMutation.mutate(member.id),
                                  });
                                }}
                              />
                            )}
                          </HStack>
                        ) : null}
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            )}
          </CardBody>
        </Card>

        {/* Pending invitations */}
        {invitations && invitations.length > 0 && (
          <Card>
            <CardHeader>
              <Heading size="md">Pending Invitations</Heading>
            </CardHeader>
            <CardBody>
              {loadingInvitations ? (
                <HStack justify="center" py={8}>
                  <Spinner />
                </HStack>
              ) : (
                <Box overflowX="auto">
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Email</Th>
                      <Th>Invited By</Th>
                      <Th>Expires</Th>
                      <Th></Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {invitations.map((invitation) => (
                      <Tr key={invitation.id}>
                        <Td>{invitation.email}</Td>
                        <Td fontSize="sm" color="text.secondary">
                          {invitation.invited_by_email}
                        </Td>
                        <Td fontSize="sm">
                          {formatDate(invitation.expires_at)}
                        </Td>
                        <Td textAlign="right">
                          <HStack spacing={1} justify="flex-end">
                            <CopyLinkButton url={invitation.join_url} />
                            {user?.is_org_admin && (
                              <Button
                                size="xs"
                                colorScheme="red"
                                variant="ghost"
                                onClick={() =>
                                  openConfirmDialog({
                                    title: "Cancel Invitation?",
                                    body: `The invitation to ${invitation.email} will be cancelled and can no longer be used to join.`,
                                    confirmLabel: "Cancel Invitation",
                                    colorScheme: "red",
                                    onConfirm: () =>
                                      cancelInvitationMutation.mutate(
                                        invitation.id,
                                      ),
                                  })
                                }
                              >
                                Cancel
                              </Button>
                            )}
                          </HStack>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
                </Box>
              )}
            </CardBody>
          </Card>
        )}
        {/* Leave Household — visible to non-primary members only */}
        {members &&
          (() => {
            const currentMember = members.find((m) => m.id === user?.id);
            if (
              !currentMember ||
              currentMember.is_primary_household_member ||
              members.length <= 1
            )
              return null;
            return (
              <Card borderColor="red.200" borderWidth="1px">
                <CardHeader>
                  <Heading size="md" color="red.600">
                    Leave Household
                  </Heading>
                </CardHeader>
                <CardBody>
                  <VStack align="stretch" spacing={4}>
                    <Text color="text.secondary" fontSize="sm">
                      Leaving will move your accounts to a new solo household.
                      You can rejoin or create a new household at any time.
                    </Text>
                    <Button
                      colorScheme="red"
                      variant="outline"
                      alignSelf="flex-start"
                      onClick={onLeaveOpen}
                    >
                      Leave Household
                    </Button>
                  </VStack>
                </CardBody>
              </Card>
            );
          })()}

        {/* Guest Access section — admin only */}
        {user?.is_org_admin && (
          <Card>
            <CardHeader>
              <HStack justify="space-between">
                <Box>
                  <Heading size="md">Guest Access</Heading>
                  <Text fontSize="sm" color="text.secondary" mt={1}>
                    Invite external users to view your household data without
                    joining as a member
                  </Text>
                </Box>
                <Button
                  colorScheme="teal"
                  size="sm"
                  onClick={onGuestInviteOpen}
                >
                  Invite Guest
                </Button>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack spacing={6} align="stretch">
                {/* Active guests */}
                {loadingGuests ? (
                  <HStack justify="center" py={4}>
                    <Spinner />
                  </HStack>
                ) : guestRecords && guestRecords.length > 0 ? (
                  <Box overflowX="auto">
                    <Text fontWeight="medium" mb={3}>
                      Active Guests
                    </Text>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Email</Th>
                          <Th>Role</Th>
                          <Th>Label</Th>
                          <Th>Since</Th>
                          <Th>Expires</Th>
                          <Th></Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {guestRecords.map((guest) => {
                          const expiresAt = guest.expires_at ? new Date(guest.expires_at) : null;
                          const daysUntilExpiry = expiresAt
                            ? Math.ceil((expiresAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24))
                            : null;
                          const expiresImminently =
                            daysUntilExpiry !== null && daysUntilExpiry <= 14 && daysUntilExpiry > 0;
                          return (
                            <Tr key={guest.id}>
                              <Td>{guest.user_email}</Td>
                              <Td>
                                <Badge
                                  colorScheme={
                                    guest.role === "advisor" ? "purple" : "gray"
                                  }
                                >
                                  {guest.role}
                                </Badge>
                              </Td>
                              <Td fontSize="sm" color="text.secondary">
                                {guest.label || "—"}
                              </Td>
                              <Td fontSize="sm">
                                {formatDate(guest.created_at)}
                              </Td>
                              <Td fontSize="sm">
                                {expiresAt ? (
                                  <VStack spacing={0.5} align="start">
                                    <Text>{formatDate(guest.expires_at!)}</Text>
                                    {expiresImminently && (
                                      <Badge colorScheme="orange" fontSize="xs">
                                        Expires in {daysUntilExpiry}d
                                      </Badge>
                                    )}
                                  </VStack>
                                ) : (
                                  <Text color="text.secondary">Never</Text>
                                )}
                              </Td>
                              <Td textAlign="right">
                                <Button
                                  size="xs"
                                  colorScheme="red"
                                  variant="ghost"
                                  onClick={() =>
                                    openConfirmDialog({
                                      title: "Revoke Guest Access?",
                                      body: `${guest.user_email} will immediately lose access to your household data.`,
                                      confirmLabel: "Revoke Access",
                                      colorScheme: "red",
                                      onConfirm: () =>
                                        revokeGuestMutation.mutate(guest.id),
                                    })
                                  }
                                >
                                  Revoke
                                </Button>
                              </Td>
                            </Tr>
                          );
                        })}
                      </Tbody>
                    </Table>
                  </Box>
                ) : (
                  <Text fontSize="sm" color="text.secondary">
                    No active guests. Invite someone to give them read-only or
                    advisory access to your household.
                  </Text>
                )}

                {/* Pending guest invitations */}
                {guestInvitations && guestInvitations.length > 0 && (
                  <Box overflowX="auto">
                    <Text fontWeight="medium" mb={3}>
                      Pending Guest Invitations
                    </Text>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Email</Th>
                          <Th>Role</Th>
                          <Th>Expires</Th>
                          <Th></Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {guestInvitations.map((inv) => (
                          <Tr key={inv.id}>
                            <Td>{inv.email}</Td>
                            <Td>
                              <Badge
                                colorScheme={
                                  inv.role === "advisor" ? "purple" : "gray"
                                }
                              >
                                {inv.role}
                              </Badge>
                            </Td>
                            <Td fontSize="sm">{formatDate(inv.expires_at)}</Td>
                            <Td textAlign="right">
                              <Button
                                size="xs"
                                colorScheme="red"
                                variant="ghost"
                                onClick={() =>
                                  openConfirmDialog({
                                    title: "Cancel Guest Invitation?",
                                    body: `The invitation to ${inv.email} will be cancelled.`,
                                    confirmLabel: "Cancel Invitation",
                                    colorScheme: "red",
                                    onConfirm: () =>
                                      cancelGuestInvitationMutation.mutate(
                                        inv.id,
                                      ),
                                  })
                                }
                              >
                                Cancel
                              </Button>
                            </Td>
                          </Tr>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Organization Preferences */}
        {orgPrefs && (
          <Card>
            <CardHeader>
              <Heading size="md">Organization Preferences</Heading>
            </CardHeader>
            <CardBody>
              <Stack spacing={4}>
                <FormControl>
                  <FormLabel>Monthly Start Day</FormLabel>
                  {user?.is_org_admin ? (
                    <NumberInput
                      value={monthlyStartDay}
                      onChange={(_, value) => setMonthlyStartDay(value)}
                      min={1}
                      max={28}
                      maxW="120px"
                    >
                      <NumberInputField />
                      <NumberInputStepper>
                        <NumberIncrementStepper />
                        <NumberDecrementStepper />
                      </NumberInputStepper>
                    </NumberInput>
                  ) : (
                    <Text fontWeight="medium">
                      {orgPrefs.monthly_start_day}
                    </Text>
                  )}
                  <FormHelperText>
                    Day of the month to start tracking (1-28). For example, set
                    to 16 to track from the 16th of each month. Transactions,
                    cash flow, and net worth calculations will be grouped
                    monthly based on this day.
                  </FormHelperText>
                </FormControl>
                {user?.is_org_admin && (
                  <Button
                    colorScheme="blue"
                    onClick={handleUpdateOrgPreferences}
                    isLoading={updateOrgMutation.isPending}
                    alignSelf="flex-start"
                  >
                    Save Preferences
                  </Button>
                )}
              </Stack>
            </CardBody>
          </Card>
        )}
      </VStack>

      {/* Leave household confirmation dialog */}
      <AlertDialog
        isOpen={isLeaveOpen}
        leastDestructiveRef={leaveCancelRef}
        onClose={onLeaveClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Leave Household?
            </AlertDialogHeader>
            <AlertDialogBody>
              <VStack align="stretch" spacing={3}>
                <Text>Are you sure you want to leave this household?</Text>
                <Alert status="warning" borderRadius="md" fontSize="sm">
                  <AlertIcon />
                  Your accounts will be moved to a new solo household. You will
                  be signed out immediately so your session refreshes.
                </Alert>
              </VStack>
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={leaveCancelRef} onClick={onLeaveClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                ml={3}
                onClick={() => leaveMutation.mutate()}
                isLoading={leaveMutation.isPending}
              >
                Leave Household
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Reusable confirmation dialog */}
      <AlertDialog
        isOpen={isConfirmOpen}
        leastDestructiveRef={confirmCancelRef}
        onClose={onConfirmClose}
        isCentered
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              {confirmConfig.title}
            </AlertDialogHeader>
            <AlertDialogBody>{confirmConfig.body}</AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={confirmCancelRef} onClick={onConfirmClose}>
                Cancel
              </Button>
              <Button
                colorScheme={confirmConfig.colorScheme}
                ml={3}
                onClick={() => {
                  confirmConfig.onConfirm();
                  onConfirmClose();
                }}
              >
                {confirmConfig.confirmLabel}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Invite modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Invite Household Member</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isInvalid={!!emailError}>
                <FormLabel>Email Address</FormLabel>
                <Input
                  type="email"
                  placeholder="member@example.com"
                  value={inviteEmail}
                  onChange={(e) => {
                    setInviteEmail(e.target.value);
                    setEmailError("");
                  }}
                />
                <FormErrorMessage>{emailError}</FormErrorMessage>
              </FormControl>
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Text fontSize="sm">
                  An invitation email will be sent if email is configured. You
                  can also copy the join link from the pending invitations table
                  and share it directly. Invitations expire after 7 days.
                </Text>
              </Alert>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleInvite}
              isLoading={inviteMutation.isPending}
            >
              Send Invitation
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Guest invite modal */}
      <Modal isOpen={isGuestInviteOpen} onClose={onGuestInviteClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Invite Guest</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isInvalid={!!guestEmailError}>
                <FormLabel>Email Address</FormLabel>
                <Input
                  type="email"
                  placeholder="guest@example.com"
                  value={guestEmail}
                  onChange={(e) => {
                    setGuestEmail(e.target.value);
                    setGuestEmailError("");
                  }}
                />
                <FormErrorMessage>{guestEmailError}</FormErrorMessage>
              </FormControl>
              <FormControl>
                <FormLabel>Role</FormLabel>
                <Select
                  value={guestRole}
                  onChange={(e) =>
                    setGuestRole(e.target.value as "viewer" | "advisor")
                  }
                >
                  <option value="viewer">Viewer (read-only)</option>
                  <option value="advisor">Advisor (can edit)</option>
                </Select>
                <FormHelperText>
                  {guestRole === "viewer"
                    ? "Viewers can see balances, transactions, and budgets — but cannot add, edit, or delete anything. Good for family members who want to stay informed."
                    : "Advisors can view everything and also add or edit accounts, transactions, and budgets. They cannot delete data or change household settings. Good for accountants or financial advisors."}
                </FormHelperText>
              </FormControl>
              <FormControl>
                <FormLabel>Label (optional)</FormLabel>
                <Input
                  placeholder='e.g. "Mom & Dad", "Financial Advisor"'
                  value={guestLabel}
                  onChange={(e) => setGuestLabel(e.target.value)}
                />
                <FormHelperText>
                  A display name to help you remember who this guest is.
                </FormHelperText>
              </FormControl>
              <FormControl>
                <FormLabel>Access Duration</FormLabel>
                <Select
                  value={guestExpiresDays}
                  onChange={(e) => setGuestExpiresDays(e.target.value)}
                >
                  <option value="">No expiry</option>
                  <option value="30">30 days</option>
                  <option value="60">60 days</option>
                  <option value="90">90 days</option>
                  <option value="365">1 year</option>
                </Select>
                <FormHelperText>
                  Guest access will be automatically revoked after this period.
                </FormHelperText>
              </FormControl>
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Text fontSize="sm">
                  Guests can view your household data without becoming a
                  household member. Their own accounts remain separate.
                  Invitations expire after 7 days.
                </Text>
              </Alert>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onGuestInviteClose}>
              Cancel
            </Button>
            <Button
              colorScheme="teal"
              onClick={handleGuestInvite}
              isLoading={guestInviteMutation.isPending}
            >
              Send Invitation
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* First-invite celebration modal */}
      <Modal
        isOpen={isCelebrationOpen}
        onClose={onCelebrationClose}
        isCentered
        size="md"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalCloseButton />
          <ModalBody py={8}>
            <VStack spacing={5} align="center">
              <CheckCircleIcon w={16} h={16} color="green.400" />
              <Heading size="lg" textAlign="center">
                Your Household Is Growing!
              </Heading>
              <Text color="text.secondary" textAlign="center">
                You just sent your first invitation to{" "}
                <Text as="span" fontWeight="semibold">
                  {celebrationEmail}
                </Text>
                . Once they accept, you'll both be able to:
              </Text>
              <VStack align="start" spacing={2} w="full" px={4}>
                <HStack spacing={2}>
                  <CheckCircleIcon color="green.400" />
                  <Text fontSize="sm">
                    View combined household net worth and spending
                  </Text>
                </HStack>
                <HStack spacing={2}>
                  <CheckCircleIcon color="green.400" />
                  <Text fontSize="sm">
                    Switch between individual and household views
                  </Text>
                </HStack>
                <HStack spacing={2}>
                  <CheckCircleIcon color="green.400" />
                  <Text fontSize="sm">
                    Share budgets, goals, and retirement plans
                  </Text>
                </HStack>
                <HStack spacing={2}>
                  <CheckCircleIcon color="green.400" />
                  <Text fontSize="sm">
                    Control data visibility with granular permissions
                  </Text>
                </HStack>
              </VStack>
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Text fontSize="sm">
                  You can manage permissions for each member from the{" "}
                  <Text as="span" fontWeight="semibold">
                    Permissions
                  </Text>{" "}
                  page once they join.
                </Text>
              </Alert>
            </VStack>
          </ModalBody>
          <ModalFooter justifyContent="center">
            <Button colorScheme="brand" onClick={onCelebrationClose} size="lg">
              Got It
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
  );
};
