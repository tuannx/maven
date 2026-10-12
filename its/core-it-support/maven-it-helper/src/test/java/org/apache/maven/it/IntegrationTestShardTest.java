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
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class IntegrationTestShardTest {

    @Test
    void unsetPropertiesLeaveEveryClassRunnable() {
        IntegrationTestShard parsed = IntegrationTestShard.parse("", "");
        assertNull(parsed.shard);
    }

    @Test
    void partialOrOutOfRangePropertiesFailClosed() {
        assertThrows(IllegalStateException.class, () -> IntegrationTestShard.parse("0", ""));
        assertThrows(IllegalStateException.class, () -> IntegrationTestShard.parse("", "2"));
        assertThrows(IllegalStateException.class, () -> IntegrationTestShard.parse("2", "2"));
        assertThrows(IllegalStateException.class, () -> IntegrationTestShard.parse("x", "2"));
    }

    @Test
    void eachSuiteClassBelongsToOneShard() throws IOException {
        Path javaRoot = Path.of("../../core-it-suite/src/test/java");
        assertTrue(Files.isDirectory(javaRoot), javaRoot.toString());
        List<String> names = new ArrayList<>();
        try (Stream<Path> files = Files.walk(javaRoot)) {
            files.filter(path -> path.getFileName().toString().startsWith("MavenIT"))
                    .filter(path -> path.getFileName().toString().endsWith(".java"))
                    .forEach(path -> {
                        String relative = javaRoot.relativize(path).toString().replace('\\', '/');
                        names.add(relative.substring(0, relative.length() - ".java".length()).replace('/', '.'));
                    });
        }
        assertTrue(names.size() > 1, "suite classes");
        int count = 2;
        int[] sizes = new int[count];
        for (String name : names) {
            int owners = 0;
            for (int shard = 0; shard < count; shard++) {
                if (IntegrationTestShard.parse(Integer.toString(shard), Integer.toString(count)).owns(name)) {
                    owners++;
                    sizes[shard]++;
                }
            }
            assertEquals(1, owners, name);
        }
        assertTrue(sizes[0] > 0);
        assertTrue(sizes[1] > 0);
    }

    @Test
    void classSegmentIsTheShardKey() {
        String id = "[engine:junit-jupiter]/[class:org.apache.maven.it.MavenITmng0095ReactorFailureBehaviorTest]"
                + "/[method:testitFailAtEnd()]";
        assertEquals(
                "org.apache.maven.it.MavenITmng0095ReactorFailureBehaviorTest", IntegrationTestShard.className(id));
        assertNull(IntegrationTestShard.className("[engine:junit-jupiter]"));
    }
}
