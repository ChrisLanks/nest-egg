/**
 * Quick Setup page — helps users get started with pre-built financial templates.
 */

import { Container, VStack } from "@chakra-ui/react";
import QuickSetupPanel from "../features/templates/components/QuickSetupPanel";

export default function QuickSetupPage() {
  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        <QuickSetupPanel />
      </VStack>
    </Container>
  );
}
