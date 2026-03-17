/**
 * Reusable contextual help hint — renders a small info icon with a tooltip.
 * Extracted from the pattern in RothConversionAnalyzer.tsx.
 */

import {
  Box,
  Icon,
  Tooltip,
  type PlacementWithLogical,
} from "@chakra-ui/react";
import { FiInfo } from "react-icons/fi";

interface HelpHintProps {
  hint: string;
  size?: "sm" | "md";
  placement?: PlacementWithLogical;
}

export function HelpHint({
  hint,
  size = "sm",
  placement = "top",
}: HelpHintProps) {
  if (!hint) return null;

  return (
    <Tooltip label={hint} placement={placement} maxW="300px">
      <Box
        as="span"
        display="inline-flex"
        ml={1}
        verticalAlign="middle"
        cursor="help"
      >
        <Icon as={FiInfo} boxSize={size === "sm" ? 3 : 4} color="text.muted" />
      </Box>
    </Tooltip>
  );
}

export default HelpHint;
