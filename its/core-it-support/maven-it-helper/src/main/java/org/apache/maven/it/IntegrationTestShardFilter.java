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

import org.junit.platform.engine.FilterResult;
import org.junit.platform.engine.TestDescriptor;
import org.junit.platform.launcher.PostDiscoveryFilter;

/**
 * Keeps each Maven IT class on one CI shard. ADR-0027.
 */
public final class IntegrationTestShardFilter implements PostDiscoveryFilter {

    private final IntegrationTestShard selection;

    public IntegrationTestShardFilter() {
        selection = IntegrationTestShard.parse(
                System.getProperty(IntegrationTestShard.SHARD_PROPERTY, ""),
                System.getProperty(IntegrationTestShard.COUNT_PROPERTY, ""));
    }

    @Override
    public FilterResult apply(TestDescriptor descriptor) {
        if (selection.shard == null) {
            return FilterResult.included("shard unset");
        }
        String className = IntegrationTestShard.className(descriptor.getUniqueId().toString());
        if (className == null || !className.contains("MavenIT")) {
            return FilterResult.included("not an integration test class");
        }
        if (selection.owns(className)) {
            return FilterResult.included("shard " + selection.shard);
        }
        return FilterResult.excluded("shard " + selection.shard + " skipped " + className);
    }
}
