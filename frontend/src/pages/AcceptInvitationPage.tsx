/**
 * Accept Household Invitation Page
 *
 * Public page for users to accept household invitations.
 * Accessed via invitation link: /accept-invite?code=<invitation_code>
 */

import {
  Box,
  Container,
  Heading,
  VStack,
  Text,
  Button,
  Card,
  CardBody,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Spinner,
  HStack,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../services/api';

interface InvitationDetails {
  email: string;
  organization_name?: string;
  invited_by_email: string;
  expires_at: string;
  status: string;
}

export const AcceptInvitationPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const invitationCode = searchParams.get('code');
  const [accepted, setAccepted] = useState(false);

  // Fetch invitation details
  const { data: invitation, isLoading, error } = useQuery<InvitationDetails>({
    queryKey: ['invitation-details', invitationCode],
    queryFn: async () => {
      const response = await api.get(`/household/invitation/${invitationCode}`);
      return response.data;
    },
    enabled: !!invitationCode && !accepted,
    retry: false,
  });

  // Accept invitation mutation
  const acceptMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/household/accept/${invitationCode}`);
      return response.data;
    },
    onSuccess: () => {
      setAccepted(true);
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    },
  });

  // Handle missing invitation code
  if (!invitationCode) {
    return (
      <Container maxW="container.md" py={16}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="center">
              <WarningIcon w={12} h={12} color="red.500" />
              <Heading size="md">Invalid Invitation Link</Heading>
              <Text color="gray.600" textAlign="center">
                The invitation link is missing or invalid. Please check the link and try again.
              </Text>
              <Button colorScheme="blue" onClick={() => navigate('/login')}>
                Go to Login
              </Button>
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <Container maxW="container.md" py={16}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="center" py={8}>
              <Spinner size="xl" color="blue.500" />
              <Text>Loading invitation details...</Text>
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // Error state
  if (error || !invitation) {
    return (
      <Container maxW="container.md" py={16}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="center">
              <WarningIcon w={12} h={12} color="red.500" />
              <Heading size="md">Invitation Not Found</Heading>
              <Text color="gray.600" textAlign="center">
                This invitation link is invalid, has expired, or has already been used.
              </Text>
              <Button colorScheme="blue" onClick={() => navigate('/register')}>
                Create New Account
              </Button>
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // Check if invitation is expired
  const isExpired = new Date(invitation.expires_at) < new Date();

  // Success state (after accepting)
  if (accepted) {
    return (
      <Container maxW="container.md" py={16}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="center">
              <CheckCircleIcon w={16} h={16} color="green.500" />
              <Heading size="lg">Invitation Accepted!</Heading>
              <Text color="gray.600" textAlign="center">
                You have successfully joined the household. You will be redirected to login in a few seconds...
              </Text>
              <Button colorScheme="blue" onClick={() => navigate('/login')}>
                Go to Login Now
              </Button>
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // Invitation expired
  if (isExpired) {
    return (
      <Container maxW="container.md" py={16}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="center">
              <WarningIcon w={12} h={12} color="orange.500" />
              <Heading size="md">Invitation Expired</Heading>
              <Text color="gray.600" textAlign="center">
                This invitation expired on{' '}
                {new Date(invitation.expires_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}.
                Please contact {invitation.invited_by_email} to send you a new invitation.
              </Text>
              <Button colorScheme="blue" onClick={() => navigate('/login')}>
                Go to Login
              </Button>
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // Invitation already accepted/declined
  if (invitation.status !== 'pending') {
    return (
      <Container maxW="container.md" py={16}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="center">
              <WarningIcon w={12} h={12} color="orange.500" />
              <Heading size="md">Invitation Already Processed</Heading>
              <Text color="gray.600" textAlign="center">
                This invitation has already been {invitation.status}.
              </Text>
              <Button colorScheme="blue" onClick={() => navigate('/login')}>
                Go to Login
              </Button>
            </VStack>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // Main invitation acceptance UI
  return (
    <Container maxW="container.md" py={16}>
      <VStack spacing={6} align="stretch">
        <Box textAlign="center">
          <Heading size="xl" mb={2}>
            Household Invitation
          </Heading>
          <Text color="gray.600">
            You've been invited to join a household on Nest Egg
          </Text>
        </Box>

        <Card>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Box>
                <Text fontWeight="bold" mb={1}>
                  Your Email:
                </Text>
                <Text fontSize="lg">{invitation.email}</Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={1}>
                  Invited By:
                </Text>
                <Text fontSize="lg">{invitation.invited_by_email}</Text>
              </Box>

              <Box>
                <Text fontWeight="bold" mb={1}>
                  Expires:
                </Text>
                <Text>
                  {new Date(invitation.expires_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Text>
              </Box>

              <Alert status="info" borderRadius="md" mt={4}>
                <AlertIcon />
                <Box>
                  <AlertTitle>What happens when you accept?</AlertTitle>
                  <AlertDescription>
                    <VStack align="start" spacing={1} mt={2}>
                      <Text fontSize="sm">• You'll join this household and see combined financial data</Text>
                      <Text fontSize="sm">• Your existing accounts will be linked to this household</Text>
                      <Text fontSize="sm">• You can view individual and combined household views</Text>
                      <Text fontSize="sm">• Household members can see shared accounts</Text>
                    </VStack>
                  </AlertDescription>
                </Box>
              </Alert>

              <HStack spacing={4} pt={4}>
                <Button
                  colorScheme="blue"
                  size="lg"
                  flex={1}
                  onClick={() => acceptMutation.mutate()}
                  isLoading={acceptMutation.isPending}
                >
                  Accept Invitation
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  flex={1}
                  onClick={() => navigate('/login')}
                >
                  Decline
                </Button>
              </HStack>

              {acceptMutation.isError && (
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <Box>
                    <AlertTitle>Failed to Accept Invitation</AlertTitle>
                    <AlertDescription>
                      {(acceptMutation.error as any)?.response?.data?.detail ||
                        'An error occurred. Please try again or contact support.'}
                    </AlertDescription>
                  </Box>
                </Alert>
              )}
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
};
