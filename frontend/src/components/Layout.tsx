/**
 * Main layout with sidebar navigation
 */

import {
  Box,
  Flex,
  VStack,
  HStack,
  Text,
  Icon,
  Button,
  Divider,
} from '@chakra-ui/react';
import {
  ViewIcon,
  RepeatIcon,
  SettingsIcon,
  StarIcon,
} from '@chakra-ui/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useLogout } from '../features/auth/hooks/useAuth';

interface NavItemProps {
  icon: any;
  label: string;
  path: string;
  isActive: boolean;
  onClick: () => void;
}

const NavItem = ({ icon, label, path, isActive, onClick }: NavItemProps) => {
  return (
    <Box
      px={4}
      py={3}
      borderRadius="md"
      cursor="pointer"
      bg={isActive ? 'brand.50' : 'transparent'}
      color={isActive ? 'brand.600' : 'gray.700'}
      fontWeight={isActive ? 'semibold' : 'medium'}
      _hover={{
        bg: isActive ? 'brand.50' : 'gray.100',
      }}
      onClick={onClick}
      transition="all 0.2s"
    >
      <HStack spacing={3}>
        <Icon as={icon} boxSize={5} />
        <Text fontSize="sm">{label}</Text>
      </HStack>
    </Box>
  );
};

export const Layout = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthStore();
  const logoutMutation = useLogout();

  const navItems = [
    { icon: ViewIcon, label: 'Dashboard', path: '/dashboard' },
    { icon: RepeatIcon, label: 'Transactions', path: '/transactions' },
    { icon: SettingsIcon, label: 'Rules', path: '/rules' },
    { icon: StarIcon, label: 'Categories', path: '/categories' },
  ];

  const handleLogout = () => {
    logoutMutation.mutate();
  };

  return (
    <Flex h="100vh" overflow="hidden">
      {/* Sidebar */}
      <Box
        w="250px"
        bg="white"
        borderRightWidth={1}
        borderColor="gray.200"
        display="flex"
        flexDirection="column"
      >
        {/* Logo/App Name */}
        <Box p={6} borderBottomWidth={1} borderColor="gray.200">
          <Text fontSize="xl" fontWeight="bold" color="brand.600">
            Nest Egg
          </Text>
          <Text fontSize="xs" color="gray.600" mt={1}>
            {user?.email}
          </Text>
        </Box>

        {/* Navigation */}
        <VStack spacing={1} p={4} flex={1} align="stretch">
          {navItems.map((item) => (
            <NavItem
              key={item.path}
              icon={item.icon}
              label={item.label}
              path={item.path}
              isActive={location.pathname === item.path}
              onClick={() => navigate(item.path)}
            />
          ))}
        </VStack>

        {/* User section */}
        <Box p={4} borderTopWidth={1} borderColor="gray.200">
          <VStack spacing={2} align="stretch">
            <Text fontSize="xs" color="gray.500" fontWeight="medium">
              {user?.first_name} {user?.last_name}
            </Text>
            <Button
              size="sm"
              variant="outline"
              colorScheme="red"
              onClick={handleLogout}
            >
              Logout
            </Button>
          </VStack>
        </Box>
      </Box>

      {/* Main content area */}
      <Box flex={1} overflowY="auto" bg="gray.50">
        <Outlet />
      </Box>
    </Flex>
  );
};
