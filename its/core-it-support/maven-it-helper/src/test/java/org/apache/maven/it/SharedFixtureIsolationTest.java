/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
package org.apache.maven.it;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SharedFixtureIsolationTest extends AbstractMavenIntegrationTestCase {

    @Test
    void mng0095CopyIsPrivateToThisTest() throws IOException {
        Path root = Files.createTempDirectory("mng0095-shared");
        String previous = System.setProperty("maven.test.tmpdir", root.toString());
        Path isolatedRoot = null;
        try {
            Path source = root.resolve("mng-0095");
            Files.createDirectories(source.resolve("subproject1"));
            Files.writeString(source.resolve("pom.xml"), "<project/>");

            Path first = extractResources("mng-0095");
            Files.writeString(first.resolve("marker.txt"), "local");
            Path second = extractResources("mng-0095");
            isolatedRoot = first.getParent().getParent();

            assertEquals(first, second);
            assertEquals("local", Files.readString(second.resolve("marker.txt")));
            assertNotEquals(source.toAbsolutePath(), first);
            assertEquals("<project/>", Files.readString(source.resolve("pom.xml")));
            assertFalse(Files.exists(source.resolve("marker.txt")));
            assertTrue(first.endsWith("mng-0095"));

            Path untouched = extractResources("test-resource");
            assertEquals(root.resolve("test-resource").toAbsolutePath(), untouched);

            SharedFixtureIsolationTest other = new SharedFixtureIsolationTest();
            Path otherDir = other.extractResources("mng-0095");
            assertNotEquals(first, otherDir);
            assertEquals("<project/>", Files.readString(otherDir.resolve("pom.xml")));
            assertFalse(Files.exists(otherDir.resolve("marker.txt")));
        } finally {
            if (previous == null) {
                System.clearProperty("maven.test.tmpdir");
            } else {
                System.setProperty("maven.test.tmpdir", previous);
            }
            deleteTree(root);
            if (isolatedRoot != null) {
                deleteTree(isolatedRoot);
            }
        }
    }

    private static void deleteTree(Path root) throws IOException {
        if (!Files.exists(root)) {
            return;
        }
        try (Stream<Path> walk = Files.walk(root)) {
            for (Path path : walk.sorted(Comparator.reverseOrder()).toList()) {
                Files.deleteIfExists(path);
            }
        }
    }
}
