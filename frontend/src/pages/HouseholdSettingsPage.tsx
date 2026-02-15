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
  FormControl,
  FormLabel,
  Input,
  FormErrorMessage,
  useToast,
  Divider,
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
} from '@chakra-ui/react';
import { EmailIcon, DeleteIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../services/api';

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
  status: 'pending' | 'accepted' | 'declined' | 'expired';
  expires_at: string;
  created_at: string;
  invited_by_email: string;
}

export const HouseholdSettingsPage: React.FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [inviteEmail, setInviteEmail] = useState('');
  const [emailError, setEmailError] = useState('');

  // Fetch household members
  const { data: members, isLoading: loadingMembers } = useQuery<HouseholdMember[]>({
    queryKey: ['household-members'],
    queryFn: async () => {
      const response = await api.get('/household/members');
      return response.data;
    },
  });

  // Fetch pending invitations
  const { data: invitations, isLoading: loadingInvitations } = useQuery<Invitation[]>({
    queryKey: ['household-invitations'],
    queryFn: async () => {
      const response = await api.get('/household/invitations');
      return response.data;
    },
  });

  // Invite member mutation
  const inviteMutation = useMutation({
    mutationFn: async (email: string) => {
      const response = await api.post('/household/invite', { email });
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Invitation sent',
        description: 'The invitation has been sent successfully.',
        status: 'success',
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['household-invitations'] });
      setInviteEmail('');
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to send invitation',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
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
        title: 'Member removed',
        description: 'The member has been removed from the household.',
        status: 'success',
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['household-members'] });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to remove member',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Cancel invitation mutation
  const cancelInvitationMutation = useMutation({
    mutationFn: async (invitationId: string) => {
      await api.delete(`/household/invitations/${invitationId}`);
    },
    onSuccess: () => {
      toast({
        title: 'Invitation cancelled',
        description: 'The invitation has been cancelled.',
        status: 'success',
        duration: 3000,
      });
      queryClient.invalidateQueries({ queryKey: ['household-invitations'] });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to cancel invitation',
        description: error.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Validate email
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) {
      setEmailError('Email is required');
      return false;
    }
    if (!emailRegex.test(email)) {
      setEmailError('Invalid email address');
      return false;
    }
    setEmailError('');
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
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        <Box>
          <Heading size="lg" mb={2}>
            Household Settings
          </Heading>
          <Text color="gray.600">
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
                You have reached the maximum of 5 household members.
                Remove a member before inviting new ones.
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {/* Members section */}
        <Card>
          <CardHeader>
            <HStack justify="space-between">
              <Heading size="md">Household Members</Heading>
              <Button
                leftIcon={<EmailIcon />}
                colorScheme="blue"
                size="sm"
                onClick={onOpen}
                isDisabled={members && members.length >= 5}
              >
                Invite Member
              </Button>
            </HStack>
          </CardHeader>
          <CardBody>
            {loadingMembers ? (
              <HStack justify="center" py={8}>
                <Spinner />
              </HStack>
            ) : (
              <VStack spacing={4} align="stretch">
                {members?.map((member) => (
                  <Card key={member.id} variant="outline">
                    <CardBody>
                      <HStack justify="space-between">
                        <HStack spacing={4}>
                          <Avatar
                            name={getDisplayName(member)}
                            size="md"
                          />
                          <Box>
                            <HStack>
                              <Text fontWeight="medium">
                                {getDisplayName(member)}
                              </Text>
                              {member.is_primary_household_member && (
                                <Badge colorScheme="purple">Primary</Badge>
                              )}
                              {member.is_org_admin && (
                                <Badge colorScheme="blue">Admin</Badge>
                              )}
                            </HStack>
                            <Text fontSize="sm" color="gray.600">
                              {member.email}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                              Joined {formatDate(member.created_at)}
                            </Text>
                          </Box>
                        </HStack>
                        {!member.is_primary_household_member && member.is_org_admin && (
                          <IconButton
                            aria-label="Remove member"
                            icon={<DeleteIcon />}
                            colorScheme="red"
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (window.confirm(`Remove ${getDisplayName(member)} from household?`)) {
                                removeMutation.mutate(member.id);
                              }
                            }}
                          />
                        )}
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
                        <Td fontSize="sm" color="gray.600">
                          {invitation.invited_by_email}
                        </Td>
                        <Td fontSize="sm">
                          {formatDate(invitation.expires_at)}
                        </Td>
                        <Td textAlign="right">
                          <Button
                            size="xs"
                            colorScheme="red"
                            variant="ghost"
                            onClick={() => {
                              if (window.confirm(`Cancel invitation to ${invitation.email}?`)) {
                                cancelInvitationMutation.mutate(invitation.id);
                              }
                            }}
                          >
                            Cancel
                          </Button>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
            </CardBody>
          </Card>
        )}
      </VStack>

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
                    setEmailError('');
                  }}
                />
                <FormErrorMessage>{emailError}</FormErrorMessage>
              </FormControl>
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Text fontSize="sm">
                  The invited member will receive an email with an invitation link.
                  They'll have 7 days to accept the invitation.
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
    </Container>
  );
};
